# -*- coding: utf-8 -*-

import os
import subprocess

import sublime

from .st3_CommandsBase.WindowCommand import stWindowCommand

class GitRepositoryCommand(stWindowCommand):
    def run(self):
        commands = [
            ("REPOSITORY: Show all modifications...", self.all_modifications),
            ("REPOSITORY: Show log...", self.log),
            ("REPOSITORY: Commit changes...", self.choose_commit_options),
        ]

        if self.window.active_view() and self.window.active_view().file_name():
            active_file = os.path.abspath(self.window.active_view().file_name())[
                len(os.path.abspath(self.path))+1:
            ]
            commands.extend([
                ("FILE: Show log", lambda: self.log(path=active_file)),
                ("FILE: Blame", lambda: self.blame_file(path=active_file)),
                ("FILE: Hide blame", lambda: self.hide_blame()),
            ])

            modified_files = self.get_all_modified_files()
            modified_file = [f for f in modified_files if f[0] == active_file]
            if modified_file:
                commands.extend(self.get_file_actions(modified_file[0][0], modified_file[0][1], parentAction=self.run))

        self.ChooseAction(commands)

    def ChooseAction(self, actions, selected="", parentAction=None, thisAction=None):
        if not thisAction:
            def _thisAction(selected, parentAction, thisAction):
                self.ChooseAction(
                    actions,
                    selected=selected,
                    parentAction=parentAction,
                    thisAction=thisAction)

            thisAction = _thisAction

        selectedIndex = 0
        if parentAction:
            actions = [("..", parentAction)] + actions
            selectedIndex = 1

        if selected:
            for i in range(len(actions)):
                if actions[i][0] == selected:
                    selectedIndex = i
                    break

        def onChoose(index):
            action = actions[index]
            action[1](
                parentAction=lambda: thisAction(selected=action[0], parentAction=parentAction, thisAction=thisAction))

        self.SelectItem(
            [a[0] for a in actions],
            onChoose,
            selectedIndex=selectedIndex)

    def not_staged_diff(self, file_name=None):
        if not file_name:
            file_name = self.window.active_view().file_name()

        subprocess.Popen(
            ["git", "diff", file_name],
            cwd=self.path)

    def staged_diff(self, file_name=None, parentAction=None):
        if not file_name:
            file_name = self.window.active_view().file_name()

        subprocess.Popen(
            ["git", "diff", "--staged", file_name],
            cwd=self.path)

    def add_to_index(self, file_name=None, parentAction=None):
        if not file_name:
            file_name = self.window.active_view().file_name()

        subprocess.Popen(
            ["git", "add", file_name],
            cwd=self.path)

    def remove_from_index(self, file_name, parentAction=None):
        assert (file_name)

        subprocess.Popen(
            ["git", "reset", "HEAD", "--", file_name],
            cwd=self.path)

    def remove_file(self, file_name, parentAction=None):
        if not sublime.ok_cancel_dialog(
            "Do you really want to remove file '{}'?".format(file_name)):
            return
        os.remove(os.path.join(self.path, file_name))

    def revert_file(self, file_name, parentAction=None):
        if not sublime.ok_cancel_dialog(
            "Do you really want to revert all changes in '{}'".format(file_name)):
            return

        subprocess.Popen(
            ["git", "checkout", "--", file_name],
            cwd=self.path)

    def get_file_actions(self, file_name, status, parentAction=None):
        assert (len(status) == 2)
        actions = []

        if status[0] == "M":
            actions.append(
                ("FILE: Diff staged for commit", lambda: self.staged_diff(file_name)))

        if status[1] != " ":
            actions.append(
                ("FILE: Add to index", lambda: self.add_to_index(file_name)))

        if status[0] != " " and status[0] != "?":
            actions.append(
                ("FILE: Remove from index", lambda: self.remove_from_index(file_name)))

        if status[1] == "M":
            actions.append(
                ("FILE: Diff not staged changes", lambda: self.not_staged_diff(file_name)))

        if "D" not in status:
            actions.extend([
                # ("FILE: Open file", lambda: self.open_file(file_name)),
                ("FILE: Remove file", lambda: self.remove_file(file_name)),
            ])

        if status != "  ":
            actions.append(
                ("FILE: Revert changes", lambda: self.revert_file(file_name)),)

        actions.append(
            ("FILE: Add to ignore", lambda: self.add_to_gitignore(file_name, parentAction=parentAction)))

        return actions

    def choose_file_action(self, file_name, status, parentAction=None):
        actions = []
        if parentAction:
            actions.append(("..", parentAction))

        actions.extend(self.get_file_actions(file_name, status, parentAction=parentAction))
        items = [a[0] for a in actions]

        def run(i):
            actions[i][1]()
            if parentAction:
                parentAction()

        self.SelectItem(
            items,
            run,
            selectedIndex=1 if parentAction else 0)

    def get_all_modified_files(self):
        p = subprocess.Popen(
            ["git", "status", '--short'],
            stdout=subprocess.PIPE,
            cwd=self.path)
        out, err = p.communicate()
        files = out.decode("utf-8").splitlines()
        files = [[f[3:], f[:2]] for f in files]
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

    def all_modifications(self, preselected=None, parentAction=None):
        actions = []
        preselectedIndex = 0
        if parentAction:
            actions.append(("..", parentAction))
            preselectedIndex += 1

        files = self.get_all_modified_files()
        for f in files:
            if f[0] == preselected:
                preselectedIndex = len(actions)

            actions.append((
                self.get_status_str(f[1]) + '\t' + f[0],
                lambda: self.choose_file_action(
                    f[0],
                    f[1],
                    parentAction=lambda: self.all_modifications(preselected=f[0], parentAction=parentAction))))

        self.SelectItem(
            [a[0] for a in actions],
            lambda i: actions[i][1](),
            selectedIndex=preselectedIndex)

    def choose_commit_options(self, parentAction):
        actions = []
        if parentAction:
            actions.append(("..", parentAction))

        actions.extend([
            ("Commit indexed changes...", self.commit),
            ("Amend last changes...", lambda: self.commit(amend=True)),
        ])

        self.SelectItem(
            [a[0] for a in actions],
            lambda i: actions[i][1](),
            selectedIndex=1 if parentAction else 0)

    def commit(self, amend=False):
        def make_commit(message):
            subprocess.Popen(
                ["git", "commit", "-m", message] + (["--amend"] if amend else []),
                cwd=self.path)

        msg = ''
        if amend:
            p = subprocess.Popen(
                ['git', 'log', '--oneline', '-1', '--format=%B'],
                stdout=subprocess.PIPE,
                cwd=self.path)
            out, err = p.communicate()
            msg = out.decode("utf-8")

        self.window.show_input_panel(
            "Enter commit message:",
            msg,
            make_commit,
            None,
            None)

    def log(self, preselectedIndex=0, path=None, parentAction=None):
        # subprocess.Popen(
        #     "gitk",
        #     cwd=self.path)

        TAG = 0
        TITLE = 1
        AUTHOR = 2
        HASH = 3
        DATE = 4

        cmd = [
            "git",
            "log",
            "--date-order",
            '--oneline',
            '-10000',
            '--format=%d!SEP!%f!SEP!%cN!SEP!%h!SEP!%ar']
        if path:
            cmd = cmd + ['--', path]

        p = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            cwd=self.path)
        out, err = p.communicate()
        commits = [c.split("!SEP!") for c in out.decode("utf-8").splitlines()]

        views = []
        for c in commits:
            views.append([
                c[TITLE].replace('-', ' ') + '\t' + c[HASH],
                (c[TAG] + " " if c[TAG] else "") + c[AUTHOR] + " " + c[DATE],
            ])

        self.SelectItem(
            views,
            lambda i: self.show_commit(
                commits[i][HASH],
                parentAction=lambda: self.log(i, path)),
            Flags = sublime.KEEP_OPEN_ON_FOCUS_LOST,
            selectedIndex=preselectedIndex)

    def show_commit(self, commit, parentAction=None, preselectedIndex=1):
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

        out, err = p.communicate()
        files = [f.split('\t') for f in out.decode("utf-8").splitlines()]
        views = [self.get_status_str(f[0]) + '\t' + f[1] for f in files]
        if parentAction:
            files = [('..', '')]  + files
            views = ['..'] + views

        def run(i):
            if parentAction and i==0:
                parentAction()
                return

            continuation = lambda: self.show_commit(
                commit=commit,
                parentAction=parentAction,
                preselectedIndex=i)

            self.choose_file_in_commit_action(
                commit=commit,
                file_name=files[i][1],
                status=files[i][0],
                continuation=continuation,
                parentAction=continuation)

        self.SelectItem(
            views,
            run,
            Flags = sublime.KEEP_OPEN_ON_FOCUS_LOST,
            selectedIndex=preselectedIndex)

    def get_file_in_commit_actions(self, commit, file_name, status):
        while len(status) < 2:
            status += ' '
        actions = [
            ("FILE: Diff", lambda: self.diff_for_file_in_commit(commit, file_name))]

        # if status[0] == "M":
        #     actions.append(
        #         ("FILE: Diff", lambda: self.diff_for_file_in_commit(commit, file_name)))

        # if status[0] != "D":
        #     actions.append(
        #         ("FILE: Revert to this revision", lambda: self.revert_file_to_commit(commit, file_name)))
        #     actions.extend([
        #         # ("FILE: Open file", lambda: self.open_file(file_name)),
        #         ("FILE: Remove file", lambda: self.remove_file(file_name)),
        #     ])

        # if status != "  ":
        #     actions.append(
        #         ("FILE: Revert changes", lambda: self.revert_file(file_name)),)

        return actions

    def choose_file_in_commit_action(self, commit, file_name, status, continuation=lambda: None, parentAction=None):
        actions = self.get_file_in_commit_actions(commit, file_name, status)
        if parentAction:
            actions = [('..', parentAction)] + actions

        items = [a[0] for a in actions]

        def run(i):
            actions[i][1]()
            continuation()

        self.SelectItem(items, run, selectedIndex=1)

    def diff_for_file_in_commit(self, commit, file):
        subprocess.Popen(
            [
                "git",
                "diff",
                commit+"^!",
                '--',
                file
            ],
            cwd=self.path)

    def blame_file(self, path, parentAction=None):
        p = subprocess.Popen(
            [
                "git",
                "blame",
                path
            ],
            stdout=subprocess.PIPE,
            cwd=self.path)

        out, err = p.communicate()

        view = self.window.active_view()
        view.erase_phantoms ("git blame")
        phantoms = []
        row = 0
        for line in out.decode("utf-8").splitlines():
            pos = view.text_point(row, 0)
            view.add_phantom (
                "git blame",
                sublime.Region(pos, pos),
                line[:line.index('+')-1].replace("  ", " .").replace("(", ""),
                sublime.LAYOUT_INLINE)
            row += 1

    def hide_blame(self, parentAction=None):
        view = self.window.active_view()
        view.erase_phantoms ("git blame")

    def add_to_gitignore(self, path, parentAction=None):
        path = os.path.normpath(path)
        def append_ignore(mask):
            with open(os.path.join(self.path, '.gitignore'), 'a') as f:
                f.write(mask + '\n')

        actions = []
        if parentAction:
            actions.append(('..', parentAction))

        def add_ignore_mask(mask):
            actions.append((mask, lambda: append_ignore(mask)))

        exts = os.path.basename(path).split('.')[1:]
        while exts:
            add_ignore_mask('.'.join(['*'] + exts))
            exts = exts[1:]

        index = len(actions)
        add_ignore_mask(os.path.basename(path))

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

        self.SelectItem([item[0] for item in actions],
                        lambda i: actions[i][1](),
                        selectedIndex=index)

