# -*- coding: utf-8 -*-

from copy import copy
from functools import partial
import os
import subprocess
import re
import shutil

import sublime

from .st3_CommandsBase.WindowCommand import stWindowCommand
from .menu import menu, action, Menu, CheckBox, Action


class GitRepositoryCommand(stWindowCommand, Menu):
    @action()
    def createRepository(self, path):
        assert os.path.isdir(path)
        self.path = path
        self.git(['init'])
        self.run()

    def full_path(self, path):
        return os.path.join(self.path, path)

    def run(self):
        self.initialMenu()(None, None)

    @menu(refresh=True)
    def initialMenu(self):
        commands = [
            ("REPOSITORY: Show all modifications...", self.all_modifications()),
            ("REPOSITORY: Show log...", self.log()),
            ("REPOSITORY: Commit changes...", self.choose_commit_options()),
            ("REPOSITORY: Branches and tags...", self.show_tags_and_branches()),
            ("REPOSITORY: Create branch from HEAD...", self.create_branch()),
            ("REPOSITORY: Create tag for HEAD...", self.create_tag()),
            ("REPOSITORY: Fetch", self.fetch()),
            ("REPOSITORY: Pull ...", self.choose_pull_options()),
            ("REPOSITORY: Push ...", self.choose_push_options()),
        ]

        if self.window.active_view() and self.window.active_view().file_name():
            active_file = os.path.abspath(self.window.active_view().file_name())[
                len(os.path.abspath(self.path))+1:
            ]
            commands.extend([
                ("FILE: Show log...", self.log(path=active_file)),
                ("FILE: Blame", self.blame_file(path=active_file)),
                ("FILE: Hide blame", self.hide_blame()),
            ])

            modified_files = self.get_all_modified_files()
            modified_file = [f for f in modified_files if f[0] == active_file]
            if modified_file:
                commands.extend(self.get_file_actions(modified_file[0][0], modified_file[0][1]))

        return commands

    def git(self, args, wait=True, silent=True, output_file=None):
        show_result = not silent and not output_file
        assert wait or not show_result
        msg = ["git"] + args
        if not silent:
            if not sublime.ok_cancel_dialog(
                "Do you really want to run following command:\n" +
                " ".join(msg)):
                return None

        print(" ".join(msg))
        p = subprocess.Popen(
            ["git"] + args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self.path)

        if wait:
            out, err = p.communicate()
            if output_file:
                with open(output_file, "wb") as f:
                    f.write(out)
            else:
                out = out.decode("utf-8")
            if err:
                sublime.message_dialog(err.decode("utf-8"))
            if show_result and out:
                sublime.message_dialog(out)
            return out

    @action()
    def diff(self, staged, file_name=None):
        if not file_name:
            file_name = self.window.active_view().file_name()

        if staged:
            self.git(["diff", "--staged", file_name], wait=False)
        else:
            self.git(["diff", file_name], wait=False)

    @action()
    def add_to_index(self, file_name=None):
        if not file_name:
            file_name = self.window.active_view().file_name()

        self.git(["add", file_name])

    @action()
    def partial_add_to_index(self, file_name=None):
        if not file_name:
            file_name = self.window.active_view().file_name()

        backup_file_name = self.full_path(file_name) + ".backup";
        shutil.copyfile(self.full_path(file_name), backup_file_name)

        self.git(["diff", file_name], wait=True)
        self.git(["add", file_name])
        shutil.move(backup_file_name, self.full_path(file_name))

    @action()
    def remove_from_index(self, file_name):
        assert (file_name)

        self.git(["reset", "HEAD", "--", file_name])

    @action()
    def remove_file(self, file_name):
        if not sublime.ok_cancel_dialog(
            "Do you really want to remove file '{}'?".format(file_name)):
            return
        os.remove(os.path.join(self.path, file_name))

    @action()
    def revert_file(self, file_name):
        if not sublime.ok_cancel_dialog(
            "Do you really want to revert all changes in '{}'".format(file_name)):
            return

        self.git(["checkout", "--", file_name])

    def get_file_actions(self, file_name, status):
        assert (len(status) == 2)
        actions = []

        if status[0] == "M":
            actions.append(
                ("FILE: Diff staged for commit", self.diff(staged=True, file_name=file_name)))

        if status[1] != " ":
            actions.extend([
                ("FILE: Add to index", self.add_to_index(file_name=file_name)),
                ("FILE: Partial add to index", self.partial_add_to_index(file_name=file_name)),
            ])

        if status[0] != " " and status[0] != "?":
            actions.append(
                ("FILE: Remove from index", self.remove_from_index(file_name=file_name)))

        if status[1] == "M":
            actions.append(
                ("FILE: Diff not staged changes", self.diff(staged=False, file_name=file_name)))

        if "D" not in status:
            actions.extend([
                # ("FILE: Open file", lambda: self.open_file(file_name)),
                ("FILE: Remove file", self.remove_file(file_name=file_name)),
            ])

        if status != "  ":
            actions.append(
                ("FILE: Revert changes", self.revert_file(file_name=file_name)))

        actions.extend([
            ("FILE: Add to ignore", self.add_to_gitignore(path=file_name)),
            ("FILE: Open", self.open_file(path=file_name))
        ])

        return actions

    @action(terminate=True)
    def open_file(self, path):
        if not os.path.isabs(path):
            path = os.path.join(self.path, path)

        self.window.open_file(path)

    @menu(refresh=True, temp=True)
    def choose_file_action(self, file_name, status):
        return self.get_file_actions(file_name, status)

    def get_all_modified_files(self):
        files = self.git(['status', '--short']).splitlines()
        files = [[f[3:].strip('"'), f[:2]] for f in files]
        return files

    @staticmethod
    def get_status_str(status):
        while len(status) < 2:
            status += ' '

        return \
            "[ ]+" if status == "??" else \
            "[+] " if status == "A " else \
            "[+]x" if status == "AM" else \
            "[ ]x" if status == " M" else \
            "[x] " if status == "M " else \
            "[x]x" if status == "MM" else \
            "[x]-" if status == "MD" else \
            "[ ]-" if status == " D" else \
            "[-] " if status == "D " else \
            status

    @menu(temp=True)
    def all_modifications_actions(self):
        return [
            ("Add all to index", self.add_all_modifications_to_index()),
            ("Remove all from index", self.remove_all_modifications_from_index()),
        ]

    @menu(refresh=True)
    def all_modifications(self):
        return [
            ("Batch actions...", self.all_modifications_actions()),
        ] + [
            Action (
                text=self.get_status_str(f[1]) + '\t' + f[0],
                func=self.choose_file_action(file_name=f[0], status=f[1]),
                id=f[0]
            ) for f in self.get_all_modified_files()
        ]

    @menu()
    def choose_commit_options(self):
        return [
            ("Commit indexed changes...", self.commit()),
            ("Amend last changes...", self.commit(amend=True)),
        ]

    @action(terminate=True)
    def commit(self, amend=False):
        def make_commit(message):
            self.git(["commit", "-m", message] + (['--amend'] if amend else []))

        bugtraqMsg = self.git(['config', 'bugtraq.message'])
        def request_bug_id(message):
            if not bugtraqMsg:
                make_commit(message)
                return

            bugInfo = re.search(bugtraqMsg.replace('%BUGID%', '\d+'), message)
            if bugInfo:
                make_commit(message)
                return

            def on_bug_id_entered(bugId):
                if bugId:
                    nonlocal message
                    message += "\n\n" + bugtraqMsg.replace("%BUGID%", bugId)

                make_commit(message)

            self.window.show_input_panel(
                "Enter bug id:",
                "",
                on_bug_id_entered,
                None,
                None)

        msg = ''
        if amend:
            msg = self.git(['log', '--oneline', '-1', '--format=%B'])

        self.window.show_input_panel(
            "Enter commit message:",
            msg,
            request_bug_id,
            None,
            None)

    @menu()
    def log(self, path=None, commit=None):
        TAG = 0
        TITLE = 1
        AUTHOR = 2
        HASH = 3
        DATE = 4

        cmd = [
            "log",
            "--date-order",
            '--oneline',
            '-10000',
            '--format=%d!SEP!%f!SEP!%cN!SEP!%h!SEP!%ar']
        if path:
            if os.path.isfile(os.path.join(self.path, path)):
                cmd = cmd + ['--follow']

            cmd = cmd + ['--', path]

        if commit:
            cmd = cmd + [commit]

        commits = [c.split("!SEP!") for c in self.git(cmd).splitlines()]

        return [
            (
                [
                    c[TITLE].replace('-', ' ') + '\t' + c[HASH],
                    (c[TAG] + " " if c[TAG] else "") + c[AUTHOR] + " " + c[DATE],
                ],
                self.show_commit(commit=c[HASH]),
            ) for c in commits
        ]

    @menu(refresh=True, temp=True)
    def choose_commit_action(self, commit):
        tags = self.git(['log', commit+'^!', '--format=%d']).strip("()\n \t")
        view = commit + " (" + tags + ")"
        tags = tags.replace('HEAD -> ', '').replace('tag: ', '').replace(', ', ' ')
        tags = [t.strip() for t in tags.split()]
        realTags = self.git(['tag', '-l', '--points-at', commit]).splitlines()

        return[
            ("Copy message to clipboard", self.copy_commit_message(commit=commit)),
            ("Show commit message", self.show_commit_message(commit=commit)),
            ("Show log ...", self.log(commit=commit)),
            ("Make revert commit", self.make_revert_commit(commit=commit)),
            ("Create branch from " + view, self.create_branch(commit=commit)),
            ("Reset to " + view + " ... ", self.choose_reset_options(commit=commit)),
            ("Cherry-pick " + view, self.cherry_pick_options(commit=commit)),
        ] + ([
            ("Checkout ...", self.choose_tag(tags=tags, action=self.checkout)),
            ("Merge ...", self.choose_tag(tags=tags, action=self.choose_merge_options)),
        ] if tags else [
            ("Checkout to " + commit, self.checkout(commit=commit)),
            ("Merge " + commit, self.choose_merge_options(commit=commit)),
        ]) + ([
            ("Remove tag ...", self.choose_tag(tags=realTags, action=self.remove_tag)),
        ] if realTags else [])

    @menu(refresh=True)
    def show_commit(self, commit):
        out = self.git(['show', '--name-status', '--format=', commit])
        files = [f.split('\t') for f in out.splitlines()]
        return [
            ("choose action ...", self.choose_commit_action(commit=commit)),
        ] + [
            (
                self.get_status_str(f[0]) + '\t' + f[1],
                self.choose_file_in_commit_action(commit=commit, file_name=f[1], status=f[0])
            ) for f in files
        ]

    @menu(temp=True)
    def choose_tag(self, tags, action):
        return [
            (t, action(t))
            for t in tags
        ]

    @menu(temp=True)
    def choose_reset_options(self, commit):
        return [
            ('Soft reset', self.reset_to_commit(commit=commit, mode='--soft')),
            ('Mixed reset', self.reset_to_commit(commit=commit, mode='')),
            ('Hard reset', self.reset_to_commit(commit=commit, mode='--hard')),
        ]

    @action()
    def reset_to_commit(self, commit, mode=''):
        self.git(['reset', mode, commit], silent=False)

    @menu(temp=True)
    def cherry_pick_options(self, commit):
        return [
            ("Cherry-pick " + commit, self.cherry_pick(commit=commit)),
            ("Cherry-pick --no-commit " + commit, self.cherry_pick(commit=commit, options=['--no-commit']))
        ]

    @action()
    def cherry_pick(self, commit, options=None):
        assert commit
        if options is None:
            options = []

        self.git(['cherry-pick'] + options + [commit], silent=False)

    @menu(temp=True)
    def choose_file_in_commit_action(self, commit, file_name, status):
        while len(status) < 2:
            status += ' '
        actions = [
            ("FILE: Diff", self.diff_for_file_in_commit(commit=commit, file=file_name)),
            ("FILE: Revert to this revision", self.revert_file_to_revision(commit=commit, file=file_name)),
            ("FILE: Revert to previous revision", self.revert_file_to_revision(commit=commit + '^', file=file_name)),
        ]

        return actions

    @action()
    def diff_for_file_in_commit(self, commit, file):
        self.git(["diff", commit+"^!", '--', file], wait=False)

    @action(terminate=True)
    def copy_commit_message(self, commit):
        sublime.set_clipboard('  \n'.join(
            self.git([
                'show',
                '--pretty=format:%H%n%aD%n%an%n%n%s%n%n%b',
                '--name-status',
                commit]).splitlines()))

    @menu()
    def show_commit_message(self, commit):
        lines = self.git([
            'show',
            '--pretty=format:%H%n%aD%n%an%n%n%s%n%n%b',
            '--name-status',
            commit]).splitlines()

        return[
            (line, self.action(partial(sublime.set_clipboard, line)))
            for line in lines
        ]


    @action(terminate=True)
    def blame_file(self, path):
        view = self.window.active_view()
        view.erase_phantoms ("git blame")
        phantoms = []
        row = 0
        for line in self.git(['blame', path]).splitlines():
            commit, text = line.split(' ', 1)
            pos = view.text_point(row, 0)
            view.add_phantom (
                "git blame",
                sublime.Region(pos, pos),
                '<a href=' + commit + '>'+commit+'</a> ' + text[:text.index('+')-1].replace("  ", " .").replace("(", ""),
                sublime.LAYOUT_INLINE,
                on_navigate=lambda href: self.show_commit(commit=href)())
            row += 1

    @action(terminate=True)
    def hide_blame(self):
        view = self.window.active_view()
        view.erase_phantoms ("git blame")

    @action()
    def append_ignore(self, mask):
        with open(os.path.join(self.path, '.gitignore'), 'a') as f:
            f.write(mask + '\n')

    @menu(temp=True)
    def add_to_gitignore(self, path):
        path = os.path.normpath(path)
        actions = []
        def add_ignore_mask(mask):
            actions.append((mask, self.append_ignore(mask)))

        exts = os.path.basename(path).split('.')[1:]

        def add_exts(prefix=""):
            _exts = copy(exts)
            while _exts:
                add_ignore_mask(os.path.join(prefix, '.'.join(['*'] + _exts)))
                _exts = _exts[1:]

        add_exts()

        selected = os.path.basename(path)
        add_ignore_mask(selected)

        if path.startswith(self.path):
            path = path[len(self.path):]

        paths = path.lstrip(os.path.sep).split(os.path.sep)
        while paths:
            if os.path.isfile(os.path.join(self.path, *paths)):
                add_ignore_mask(os.path.sep + os.path.sep.join(paths))
                add_exts( os.path.sep + os.path.sep.join(paths[:-1]) )
            else:
                add_ignore_mask(os.path.sep + os.path.sep.join(paths + ['*']))
            paths = paths[:-1]

        return actions, selected

    @menu()
    def show_tags_and_branches(self):
        branches = self.git(['branch', '--all']).splitlines()
        tags = self.git(['tag']).splitlines()
        return [
            ("Branch " + b, self.show_branch(branch=b))
            for b in branches if " -> " not in b
        ] + [
            ("Tag " + t, self.choose_commit_action(commit=t))
            for t in tags
        ]

    @menu(temp=True)
    def choose_merge_options(self, commit):
        return [
            ("Merge", partial(self.merge, commit=commit)()),
            CheckBox('Deny fast-forward', id='--no-ff'),
        ]

    @action(terminate=True)
    def merge(self, commit, options=None):
        if options is None:
            options = []

        self.git(['merge', commit] + options, silent=False)

    @action(terminate=True)
    def create_branch(self, commit=""):
        def impl(branch_name):
            self.git(
                [
                    'branch',
                    branch_name
                ] + ([commit] if commit else []),
                silent=False)

        self.window.show_input_panel(
            "Enter new branch name:",
            "",
            impl,
            None,
            None)

    @menu(temp=True)
    def show_branch(self, branch):
        active_branch = (branch[0] == '*')
        branch = branch.strip()

        return [
            ("Show log ...", self.log(commit=branch)),
            ("Merge " + branch, self.choose_merge_options(commit=branch)),
            ("Checkout " + branch, self.checkout(commit=branch)),
            ("Reset " + branch + ' ...', self.choose_reset_options(commit=branch)),
            ("Delete " + branch, self.delete_branch(commit=branch)),
        ] if not active_branch else [
        ]

    @action(terminate=True)
    def checkout(self, commit):
        assert commit
        self.git(['checkout', commit], silent=False)

    @action(terminate=True)
    def delete_branch(self, branch):
        assert branch
        self.git(['branch', '-d', branch], silent=False)

    @action(terminate=True)
    def create_tag(self, commit=None):
        def impl(tag):
            self.git(['tag', tag] + ([commit] if commit else []))

        self.window.show_input_panel(
            "Enter tag:",
            "",
            impl,
            None,
            None)

    @action()
    def remove_tag(self, tag):
        self.git(["tag", '-d', tag], silent=False)

    @action()
    def make_revert_commit(self, commit):
        self.git(["revert", "--no-edit", commit], silent=False)

    @action()
    def fetch(self):
        self.git(['fetch'])

    @menu(temp=True)
    def choose_pull_options(self):
        return [
            ("Pull and rebase", self.pool(['--rebase'])),
            ("Pull fast forward only", self.pool(['--ff-only'])),
        ]

    @menu(temp=True)
    def choose_push_options(self):
        return [
            ("Push current branch", self.push(['-u', 'origin', 'HEAD'])),
            ("Pull ALL branches", self.push(['--all'])),
        ]

    @action()
    def pool(self, options):
        self.git(['pull'] + options, silent=False)

    @action()
    def push(self, options):
        self.git(['push'] + options, silent=False)


    @action()
    def revert_file_to_revision(self, commit, file):
        self.git(
            ['show', commit+":"+file],
            silent=False,
            output_file=os.path.join(self.path, file))

    @action()
    def add_all_modifications_to_index(self):
        self.git(['add', '-A'])

    @action()
    def remove_all_modifications_from_index(self):
        self.git(['reset', 'HEAD', '--', '.'])
