# -*- coding: utf-8 -*-

from functools import partial

import sublime

from .st3_CommandsBase.WindowCommand import stWindowCommand


class Action:
    def __init__(self, text, func, id=None):
        self.id = id if id else text
        self.text = text
        self.func = func


def  menu(refresh=False, temp=False):
    def _menu(getActions):
        def impl(self, *args, **kwargs):
            return self.menu(
                getActions=partial(getActions, self, *args, **kwargs),
                refresh=refresh,
                temp=temp)

        return impl

    return _menu


def action(terminate=False):
    def _action(func):
        def impl(self, *args, **kwargs):
            return self.action(
                func=partial(func, self, *args, **kwargs),
                terminate=terminate)

        return impl

    return _action

class Menu:
    def menu(self, getActions, refresh=False, temp=False):
        def impl(parent, selectedId):
            actions = getActions()
            defaultSelectedId = None
            if isinstance(actions, tuple):
                assert len(actions) == 2
                actions, defaultSelectedId = actions[0], actions[1]

            assert isinstance(actions, list)
            if actions and isinstance(actions[0], tuple):
                actions = [Action(a[0], a[1]) for a in actions]

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

    def action(self, func, terminate=False):
        def impl(parent, selectedId):
            func()
            if not terminate and parent:
                parent()

        return impl


class TestMenuCommand(stWindowCommand, Menu):
    def run(self):
        self.buildMenu(prefix="")(parent=None, selectedId=None)

    @menu()
    def buildMenu(self, prefix):
        return [
            (prefix + "menu...", self.buildMenu(prefix=prefix+"menu/")),
            (prefix + "temporary menu", self.temporaryMenu()),
            (prefix + "action", self.action(func=partial(sublime.message_dialog, prefix+"action is called"))),
            (prefix + "test action", self.testAction()),
            (prefix + "terminated action", self.terminatedAction()),
        ]

    @menu(temp=True)
    def temporaryMenu(self):
        return [
            ("usual menu", self.buildMenu(prefix="temp/")),
            ("print", self.testAction()),
            ("print and terminate", self.terminatedAction),
        ]

    @action()
    def testAction(self):
        print("test action runned")

    @action(terminate=True)
    def terminatedAction(self):
        print("action runned and menu should not appears again")
