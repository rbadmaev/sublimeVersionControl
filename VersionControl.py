import sublime, os
from glob import glob
from .st3_CommandsBase.WindowCommand import stWindowCommand
# from .SvnRepository import SvnRepositoryCommand
from .GitRepository import GitRepositoryCommand
from .menu import Menu, menu

class VersionControlCommand(stWindowCommand, Menu):

    def _DetermineVersionControlSystem(Self):
        repositories = []
        path = Self.window.active_view().file_name()
        while True:
            # if glob(path + "\\.svn") != []:
            #     repositories += [SvnRepositoryCommand(Self.window, path)]
            # if glob(path + "\\.hg") != []:
            #     repositories += [SvnRepositoryCommand(Self.window, path)]
            if glob(os.path.join(path, ".git")) != []:
                git_rep = GitRepositoryCommand(Self.window)
                git_rep.path = path
                repositories += [git_rep]

            newpath = os.path.dirname(path)
            if newpath == path:
                break
            path = newpath
        return repositories

    def run(Self):
        repositories = Self._DetermineVersionControlSystem()

        if len(repositories) == 0:
            Self.create_repository()(None, None)
            return

        if len(repositories) == 1:
            repositories[0].run()
            return

        Self.SelectItem(
            [v.Name() + ": " + v.path for v in repositories],
            lambda index: repositories[index].run())

    @menu()
    def create_repository(self):
        if not self.window.active_view().file_name():
            return []

        return [
            (
                'Create GIT repository...',
                self.chooseRepositoryPath(GitRepositoryCommand)
            ),
        ]

    @menu()
    def chooseRepositoryPath(self, repository):
        path = os.path.dirname(self.window.active_view().file_name())
        paths = [path]
        while path != os.path.dirname(path):
            path = os.path.dirname(path)
            paths.append(path)

        return [
            (
                path,
                repository(self.window).createRepository(path)
            ) for path in paths
        ]
