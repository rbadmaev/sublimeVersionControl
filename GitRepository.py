# -*- coding: utf-8 -*-

import os
import subprocess

import sublime

from .st3_CommandsBase.WindowCommand import stWindowCommand


class GitRepositoryCommand(stWindowCommand):
    def run(self):
        commands = [
            ("REPOSITORY: Show all modifications", self.all_modifications),
            ("REPOSITORY: Show log", self.log),
            ("REPOSITORY: Commit changes", self.commit),
        ]

        if self.window.active_view() and self.window.active_view().file_name():
            active_file = os.path.abspath(self.window.active_view().file_name())[
                len(os.path.abspath(self.path))+1:
            ]
            modified_files = self.get_all_modified_files()
            active_file = [f for f in modified_files if f[0] == active_file]
            if active_file:
                commands.extend(self.get_file_actions(active_file[0][0], active_file[0][1]))


        items = [c[0] for c in commands]
        self.SelectItem(items, lambda i: commands[i][1]())

    def not_staged_diff(self, file_name=None):
        if not file_name:
            file_name = self.window.active_view().file_name()

        subprocess.Popen(
            ["git", "diff", file_name],
            cwd=self.path)

    def staged_diff(self, file_name=None):
        if not file_name:
            file_name = self.window.active_view().file_name()

        subprocess.Popen(
            ["git", "diff", "--staged", file_name],
            cwd=self.path)

    def add_to_index(self, file_name=None):
        if not file_name:
            file_name = self.window.active_view().file_name()

        subprocess.Popen(
            ["git", "add", file_name],
            cwd=self.path)

    def remove_from_index(self, file_name):
        assert (file_name)

        subprocess.Popen(
            ["git", "reset", "HEAD", "--", file_name],
            cwd=self.path)

    def remove_file(self, file_name):
        if not sublime.ok_cancel_dialog(
            "Do you really want to remove file '{}'?".format(file_name)):
            return
        os.remove(os.path.join(self.path, file_name))

    def revert_file(self, file_name):
        if not sublime.ok_cancel_dialog(
            "Do you really want to revert all changes in '{}'".format(file_name)):
            return

        subprocess.Popen(
            ["git", "checkout", "--", file_name],
            cwd=self.path)

    def get_file_actions(self, file_name, status):
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

        return actions

    def choose_file_action(self, file_name, status, continuation=lambda: None):
        actions = self.get_file_actions(file_name, status)
        items = [a[0] for a in actions]

        def run(i):
            actions[i][1]()
            continuation()

        self.SelectItem(
            items,
            run)

    def get_all_modified_files(self):
        p = subprocess.Popen(
            ["git", "status", '--short'],
            stdout=subprocess.PIPE,
            cwd=self.path)
        out, err = p.communicate()
        files = out.decode("utf-8").splitlines()
        files = [[f[3:], f[:2]] for f in files]
        return files

    def all_modifications(self, preselected=None):
        def get_status_str(status):
            assert (len(status) == 2)
            return \
                "[ ]+ " if status == "??" else \
                "[+]  " if status == "A " else \
                "[+]x " if status == "AM" else \
                "[ ]x " if status == " M" else \
                "[x]  " if status == "M " else \
                "[x]x " if status == "MM" else \
                "[x]- " if status == "MD" else \
                "[ ]- " if status == " D" else \
                "[-]  " if status == "D " else \
                status

        files = self.get_all_modified_files()
        file_views = [get_status_str(f[1]) + f[0] for f in files]
        preselectedIndex = 0
        if preselected:
            for i in range(len(files)):
                if files[i][0] == preselected:
                    preselectedIndex = i
                    break

        self.SelectItem(
            file_views,
            lambda i: self.choose_file_action(
                files[i][0],
                files[i][1],
                lambda: self.all_modifications(files[i][0])),
            selectedIndex=preselectedIndex)

    def commit(self):
        def make_commit(message):
            subprocess.Popen(
                ["git", "commit", "-m", message],
                cwd=self.path)
        self.window.show_input_panel(
            "Enter commit message:",
            "",
            make_commit,
            None,
            None)

    def log(self):
        # subprocess.Popen(
        #     "gitk",
        #     cwd=self.path)

        TAG = 0
        TITLE = 1
        AUTHOR = 2
        HASH = 3
        DATE = 4

        p = subprocess.Popen([
            "git",
            "log",
            "--date-order",
            '--oneline',
            '-1000',
            '--format=%d!SEP!%f!SEP!%cN!SEP!%h!SEP!%ar'],
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
            lambda i: self.show_commit(commits[i][HASH]),
            Flags = sublime.KEEP_OPEN_ON_FOCUS_LOST)

    def show_commit(self, commit, preselectedIndex=0):
        p = subprocess.Popen(
            [
                "git",
                "show",
                "--name-only",
                '--format=',
                commit
            ],
            # [
            #     "git",
            #     "diff-tree",
            #     "--no-commit-id",
            #     "--name-only",
            #     '-r',
            #     commit
            # ],
            stdout=subprocess.PIPE,
            cwd=self.path)
        out, err = p.communicate()
        files = out.decode("utf-8").splitlines()

        def run(i):
            self.diff_for_file_in_commit(commit, files[i])
            self.show_commit(commit, i)

        self.SelectItem(
            files,
            run,
            Flags = sublime.KEEP_OPEN_ON_FOCUS_LOST,
            selectedIndex=preselectedIndex)

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
