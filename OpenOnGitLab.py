
import sublime, sublime_plugin
import os, glob, subprocess
import webbrowser
import re

class OpenOnGitlabCommand(sublime_plugin.WindowCommand):

    def run(self, params = []):
        url = self.getLink()
        print (url)
        webbrowser.open(url)

    def getRelativePath(self):
        folder, path = os.path.split(self.window.active_view().file_name())
        def isAGitRoot(folder):
            return os.path.exists(os.path.join(folder, ".git"))

        while not isAGitRoot(folder):
            next_folder, sub = os.path.split(folder)
            if folder == next_folder:
                return None

            folder = next_folder
            path = sub + '/' + path

        return path

    def getLink(self):
        p = subprocess.Popen(["git", "config", "--get", "remote.origin.url"],
            stdout=subprocess.PIPE,
            cwd=os.path.dirname(self.window.active_view().file_name()))
        url, err = p.communicate()
        url = url.decode().strip()
        url = re.sub('[^/@]*@', '', url)
        if not url.startswith("https://"):
            url = "https://" + re.sub(':', '/', url)

        if len(url) > 4 and url[-4:] == ".git":
            url = url[:-4]

        p = subprocess.Popen(["git", "rev-parse", "--abbrev-ref", "HEAD"],
            stdout=subprocess.PIPE,
            cwd=os.path.dirname(self.window.active_view().file_name()))
        branch, err = p.communicate()
        branch = branch.decode().strip()

        p = subprocess.Popen(["git", "rev-parse", "origin/" + branch],
            stdout=subprocess.PIPE,
            cwd=os.path.dirname(self.window.active_view().file_name()))
        revision, err = p.communicate()
        revision = revision.decode().strip()

        row, col = self.window.active_view().rowcol(self.window.active_view().sel()[0].begin())

        return url + '/blob/' + revision + '/' + self.getRelativePath() + '#L' + str(row + 1)

