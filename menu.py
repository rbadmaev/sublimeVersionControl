# -*- coding: utf-8 -*-

from functools import partial

import sublime

from .st3_CommandsBase.WindowCommand import stWindowCommand


class Action:
    def __init__(self, text, func, id=None):
        super(Action, self).__init__()
        self.id = id if id else text
        self.text = text
        self.func = func


class Menu:
    def menu(self, getActions, refresh=False, temp=False):
        def impl(parent, selectedId):
            actions, defaultSelectedId = getActions()

            selectedIndex = 0
            if parent:
                selectedIndex = 1
                caption = ".." if not actions or isinstance(actions[0].text, str) else ["..", ""]
                actions = [Action(caption, parent)] + actions

            if not selectedId:
                selectedId = defaultSelectedId

            if selectedId:
                for i in range(len(actions)):
                    if actions[i].id == selectedId:
                        selectedIndex = i
                        break

            def show(selectedIndex):
                def onSelect(index):
                    if parent and index == 0:
                        parent()
                        return

                    action = actions[index]
                    thisMenu = (
                        parent if temp else
                        partial(show, index) if not refresh else
                        partial(impl, parent=parent, selectedId=action.id))

                    action.func(parent=thisMenu, selectedId=None)

                self.SelectItem(
                    [a.text for a in actions],
                    onSelect,
                    selectedIndex=selectedIndex)

            show(selectedIndex)

        return impl

    def action(self, func):
        def impl(parent, selectedId):
            func()
            if parent:
                parent()

        return impl


class TestMenuCommand(stWindowCommand, Menu):
    def run(self):
        self.menu(partial(self.buildMenu, ""))(parent=None, selectedId=None)

    def buildMenu(self, prefix):
        return ([
            Action(prefix + "menu...", self.menu(getActions=partial(self.buildMenu, prefix=prefix+"menu/"))),
            Action(prefix + "action", self.action(func=partial(sublime.message_dialog, prefix+"action is called")))
        ], None)

