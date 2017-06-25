# -*- coding: utf-8 -*-

import os
import subprocess

import sublime

from .st3_CommandsBase.WindowCommand import stWindowCommand
from .menu import Menu, menu, action


class GitRepositoryCommand(stWindowCommand, Menu):
    def run(self):
        self.initialMenu()(None, None)

    @menu(refresh=True)
    def initialMenu(self):
        commands = [
            ("REPOSITORY: Show all modifications...", self.all_modifications()),
            ("REPOSITORY: Show log...", self.log()),
            ("REPOSITORY: Commit changes...", self.choose_commit_options()),
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

    def git(self, args, wait=True):
        msg = ["git"] + args
        print(" ".join(msg))
        p = subprocess.Popen(
            ["git"] + args,
            stdout=subprocess.PIPE,
            cwd=self.path)

        if wait:
            out, err = p.communicate()
            return out.decode("utf-8")

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
            actions.append(
                ("FILE: Add to index", self.add_to_index(file_name=file_name)))

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

        actions.append(
            ("FILE: Add to ignore", self.add_to_gitignore(file_name=file_name)))

        return actions

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

    @menu(refresh=True)
    def all_modifications(self):
        return [
            (
                self.get_status_str(f[1]) + '\t' + f[0],
                self.choose_file_action(file_name=f[0], status=f[1])
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

        msg = ''
        if amend:
            msg = self.git(['log', '--oneline', '-1', '--format=%B'])

        self.window.show_input_panel(
            "Enter commit message:",
            msg,
            make_commit,
            None,
            None)

    @menu()
    def log(self, path=None):
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
            cmd = cmd + ['--', path]

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

    @menu()
    def show_commit(self, commit):
        p = subprocess.Popen(
            [
                "git",
                "show",
                "--name-status",
                '--format=',
                commit
            ],
            stdout=subprocess.PIPE,
            cwd=self.path)

        out = self.git(['show', '--name-status', '--format=', commit])
        files = [f.split('\t') for f in out.splitlines()]
        return [
            (
                self.get_status_str(f[0]) + '\t' + f[1],
                self.choose_file_in_commit_action(commit=commit, file_name=f[1], status=f[0])
            ) for f in files
        ]

    @menu(temp=True)
    def choose_file_in_commit_action(self, commit, file_name, status):
        while len(status) < 2:
            status += ' '
        actions = [
            ("FILE: Diff", self.diff_for_file_in_commit(commit=commit, file=file_name))]

        return actions

    @action()
    def diff_for_file_in_commit(self, commit, file):
        self.git(["diff", commit+"^!", '--', file], wait=False)

    @action(terminate=True)
    def blame_file(self, path):
        view = self.window.active_view()
        view.erase_phantoms ("git blame")
        phantoms = []
        row = 0
        for line in self.git(['blame', path]).splitlines():
            pos = view.text_point(row, 0)
            view.add_phantom (
                "git blame",
                sublime.Region(pos, pos),
                line[:line.index('+')-1].replace("  ", " .").replace("(", ""),
                sublime.LAYOUT_INLINE)
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
        while exts:
            add_ignore_mask('.'.join(['*'] + exts))
            exts = exts[1:]

        selected = os.path.basename(path)
        add_ignore_mask(selected)

        if path.startswith(self.path):
            path = path[len(self.path):]

        paths = path.lstrip(os.path.sep).split(os.path.sep)
        while paths:
            if os.path.isfile(os.path.join(self.path + os.path.sep.join(paths))):
                add_ignore_mask(os.path.sep + os.path.sep.join(paths))
                is_file = False
            else:
                add_ignore_mask(os.path.sep + os.path.sep.join(paths + ['*']))
            paths = paths[:-1]

        return actions, selected

