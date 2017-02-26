# -*- coding: utf-8 -*-

import os
import subprocess

from .st3_CommandsBase.WindowCommand import stWindowCommand


class GitRepositoryCommand(stWindowCommand):
    def run(self):
        commands = [
            ("Show all modifications", self.all_modifications),
            ("Commit changes", self.commit),
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
            stdout=subprocess.PIPE,
            cwd=self.path)

    def remove_from_index(self, file_name):
        assert (file_name)

        subprocess.Popen(
            ["git", "rm", "--cached", file_name],
            stdout=subprocess.PIPE,
            cwd=self.path)

    def remove_file(self, file_name):
        self.window.run_command("remove_custom_file", file_name)

    def get_file_actions(self, file_name, status):
        assert (len(status) == 2)
        actions = []
        if status[1] != " ":
            actions.append(
                ("Add to index", lambda: self.add_to_index(file_name)))

        if status[0] != " " and status[0] != "?":
            actions.append(
                ("Remove from index", lambda: self.remove_from_index(file_name)))

        if status[0] == "M":
            actions.append(
                ("Diff staged for commit", lambda: self.staged_diff(file_name)))

        if status[1] == "M":
            actions.append(
                ("Diff not staged changes", lambda: self.not_staged_diff(file_name)))

        if "D" not in status:
            actions.extend([
                # ("Open file", lambda: self.open_file(file_name)),
                ("Remove file", lambda: self.remove_file(file_name)),
            ])

        return actions

    def choose_file_action(self, file_name, status):
        actions = self.get_file_actions(file_name, status)
        items = [a[0] for a in actions]
        self.SelectItem(
            items,
            lambda i: actions[i][1]())

    def get_all_modified_files(self):
        p = subprocess.Popen(
            ["git", "status", '--short'],
            stdout=subprocess.PIPE,
            cwd=self.path)
        out, err = p.communicate()
        files = out.decode("utf-8").splitlines()
        files = [[f[3:], f[:2]] for f in files]
        return files

    def all_modifications(self):
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
        self.SelectItem(
            file_views,
            lambda i: self.choose_file_action(files[i][0], files[i][1]))

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
