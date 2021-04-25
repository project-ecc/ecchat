#!/usr/bin/env python3
# coding: UTF-8

import urwid

################################################################################
## urwid extension classes #####################################################
################################################################################

class GridFlowPlus(urwid.GridFlow):

	def keypress(self, size, key):

		if isinstance(key, str):

			if key in ('tab', ):

				if self.focus_position == len(self.contents) - 1:

					self.focus_position = 0

				else:

					self.focus_position += 1

				return

			if key in ('Y', 'y', 'O', 'o'): # Yes / OK

				self.focus_position = 0

				return super().keypress(size, 'enter')

			if key in ('esc', 'N', 'n', 'C', 'c'): # ESCAPE / No / Cancel

				self.focus_position = 1

				return super().keypress(size, 'enter')

		return super().keypress(size, key)

################################################################################

class YesNoDialog(urwid.WidgetWrap):

	signals = ['commit']

	def __init__(self, text, loop):

		self.loop = loop

		self.parent = self.loop.widget

		self.body = urwid.Filler(urwid.Text(text))

		self.frame = urwid.Frame(self.body, focus_part = 'body')

		self.view = urwid.Padding(self.frame, ('fixed left', 2), ('fixed right' , 2))
		self.view = urwid.Filler (self.view,  ('fixed top' , 1), ('fixed bottom', 1))
		self.view = urwid.LineBox(self.view)
		self.view = urwid.Overlay(self.view, self.parent, 'center', len(text) + 6, 'middle', 7)

		self.frame.footer = GridFlowPlus([urwid.AttrMap(urwid.Button('Yes', self.on_yes), 'btn_nm', 'btn_hl'),
			                              urwid.AttrMap(urwid.Button('No' , self.on_no ), 'btn_nm', 'btn_hl')],
			                             7, 3, 1, 'center')

		self.frame.focus_position = 'footer'

		super().__init__(self.view)

	############################################################################

	def on_yes(self, *args, **kwargs):

		self.loop.widget = self.parent

		urwid.emit_signal(self, 'commit')

	############################################################################

	def on_no(self, *args, **kwargs):

		self.loop.widget = self.parent

	############################################################################

	def show(self):

		self.loop.widget = self.view

################################################################################

class PassphraseEdit(urwid.Edit):

	def __init__(self, on_enter, on_cancel, on_tab, **kwargs):

		self.on_enter  = on_enter
		self.on_cancel = on_cancel
		self.on_tab    = on_tab

		super().__init__(**kwargs)

	############################################################################

	def keypress(self, size, key):

		if isinstance(key, str):

			if key in ('enter', ):

				self.on_enter()

				return

			if key in ('esc', ):

				self.on_cancel()

				return

			if key in ('tab', ):

				self.on_tab()

				return

		return super().keypress(size, key)

################################################################################

class PassphraseDialog(urwid.WidgetWrap):

	signals = ['commit']

	def __init__(self, text, loop):

		self.text = text
		self.loop = loop

		self.parent = self.loop.widget

		self.label = urwid.Text(self.text)

		self.input = PassphraseEdit(self.on_ok, self.on_cancel, self.on_tab, multiline=False, wrap = 'clip', allow_tab = False, mask='*')

		self.body  = urwid.Pile([urwid.Filler(self.label), urwid.Filler(urwid.AttrMap(self.input, 'header'))], 1)

		self.frame = urwid.Frame(self.body, focus_part = 'body')

		self.view = urwid.Padding(self.frame, ('fixed left', 2), ('fixed right' , 2))
		self.view = urwid.Filler (self.view,  ('fixed top' , 1), ('fixed bottom', 1))
		self.view = urwid.LineBox(self.view)
		self.view = urwid.Overlay(self.view, self.parent, 'center', len(text) + 6, 'middle', 9)

		self.frame.footer = GridFlowPlus([urwid.AttrMap(urwid.Button('  OK  ',  self.on_ok),     'btn_nm', 'btn_hl'),
			                              urwid.AttrMap(urwid.Button('Cancel' , self.on_cancel), 'btn_nm', 'btn_hl')],
			                             10, 3, 1, 'center')

		self.frame.focus_position = 'body'

		super().__init__(self.view)

	############################################################################

	def on_ok(self, *args, **kwargs):

		self.loop.widget = self.parent

		urwid.emit_signal(self, 'commit', True, self.input.get_edit_text())

	############################################################################

	def on_cancel(self, *args, **kwargs):

		self.loop.widget = self.parent

		urwid.emit_signal(self, 'commit', False, '')

	############################################################################

	def on_tab(self, *args, **kwargs):

		self.frame.focus_position = 'footer'

	############################################################################

	def show(self):

		self.loop.widget = self.view

################################################################################

class MessageListBox(urwid.ListBox):

	def __init__(self, body):

		super().__init__(body)

	############################################################################

	def render(self, size, *args, **kwargs):

		self.last_render_size = size

		return super().render(size, *args, **kwargs)

	############################################################################

	def key(self, key):

		super().keypress(self.last_render_size, key)

	############################################################################

	def mouse_event(self, size, event, button, col, row, focus):

		if button in (4, 5): # mouse wheel

			self.key({4 : 'up', 5 : 'down'} [button])

################################################################################

class FrameFocus(urwid.Frame):

	def __init__(self, body, header=None, footer=None, focus_part='body'):

		self.focus_part = focus_part

		super().__init__(body, header, footer, focus_part)

	############################################################################

	def mouse_event(self, size, event, button, col, row, focus):

		if button in (4, 5): # mouse wheel

			super().mouse_event(size, event, button, col, row, focus)

		self.set_focus(self.focus_part)

################################################################################

class MessageWalker(urwid.SimpleListWalker):

	def __init__(self):

		self.qual = []
		self.text = []
		self.uuid = []

		self.recallOffset = 0
		self.uuidAtOffset = ''

		super().__init__([])

	############################################################################

	def append(self, qual, text, uuid):

		self.qual.append(qual)
		self.text.append(text)
		self.uuid.append(uuid)

		self.recallOffset = 0
		self.uuidAtOffset = ''

		super().append(urwid.Text(text))

############################################################################

	def replace(self, qual, text, uuid):

		self.recallOffset = 0
		self.uuidAtOffset = ''

		for index, _uuid in enumerate(self.uuid):

			if uuid == _uuid:

				assert self.qual[index] == qual

				self[index].set_text(text)

				self.text[index] = text

				break

	############################################################################

	def set_markup_style(self, uuid, element, style):

		for index, _uuid in enumerate(self.uuid):

			if uuid == _uuid:

				markup = self.text[index]

				(old_style, text) = markup[element]

				markup[element] = (style, text)

				self[index].set_text(markup)

				self.text[index] = markup

				break

	############################################################################

	def recall(self, qual, element, direction):

		text = ''

		self.recallOffset = min(0, self.recallOffset + direction)

		if self.recallOffset < 0:

			scan_index = len(self) - 1

			qual_found = 0

			while scan_index >= 0:

				if self.qual[scan_index] == qual:

					self.uuidAtOffset = self.uuid[scan_index]

					markup = self.text[scan_index]

					(style, text) = markup[element]

					qual_found += 1

					if qual_found + self.recallOffset == 0:

						self.set_focus(scan_index)

						break

				scan_index -= 1

			if qual_found + self.recallOffset < 0:

				self.recallOffset += 1

		return text

	############################################################################

	def recall_uuid(self):

		return self.uuidAtOffset

################################################################################
