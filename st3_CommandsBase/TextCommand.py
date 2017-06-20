import sublime, sublime_plugin

def NoneFunction():
	return

class stTextCommand(sublime_plugin.TextCommand):
	def SelectItem(Self, Items, OnSelect, OnCancel = NoneFunction):
		sublime.set_timeout(
			lambda: Self.view.window().show_quick_panel(
				Items,
				lambda index: OnSelect(index) if index > -1 else OnCancel()),
			0)