import sublime, sublime_plugin

def NoneFunction():
	return

class stWindowCommand(sublime_plugin.WindowCommand):
	def SelectItem(Self, Items, OnSelect, OnCancel = NoneFunction):
		sublime.set_timeout(
			lambda: Self.window.show_quick_panel(
				Items,
				lambda index: OnSelect(index) if index > -1 else OnCancel()),
			0)