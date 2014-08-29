from rezgui.qt import QtCore, QtGui
from rez.exceptions import RezError
from rez.packages import get_completions, iter_packages
from rez.vendor.version.requirement import Requirement


class PackageLineEdit(QtGui.QLineEdit):

    focusOutViaKeyPress = QtCore.Signal(str)
    focusOut = QtCore.Signal(str)
    focusIn = QtCore.Signal()

    def __init__(self, settings=None, parent=None, family_only=False):
        super(PackageLineEdit, self).__init__(parent)
        self.settings = settings
        self.family_only = family_only
        self.default_style = None

        self.completer = QtGui.QCompleter(self)
        self.completer.setCompletionMode(QtGui.QCompleter.PopupCompletion)
        self.completions = QtGui.QStringListModel(self.completer)
        self.completer.setModel(self.completions)
        self.setCompleter(self.completer)

        self.textEdited.connect(self._textEdited)

    def mouseReleaseEvent(self, event):
        if not self.hasSelectedText():
            self.completer.complete()

    def event(self, event):
        # keyPressEvent does not capture tab
        if event.type() == QtCore.QEvent.KeyPress \
                and event.key() in (QtCore.Qt.Key_Tab,
                                    QtCore.Qt.Key_Enter,
                                    QtCore.Qt.Key_Return):
            self._update_status()
            self.focusOutViaKeyPress.emit(self.text())
            return True
        return super(PackageLineEdit, self).event(event)

    def focusInEvent(self, event):
        self.focusIn.emit()
        return super(PackageLineEdit, self).focusInEvent(event)

    def focusOutEvent(self, event):
        self._update_status()
        self.focusOut.emit(self.text())
        return super(PackageLineEdit, self).focusOutEvent(event)

    def refresh(self):
        self._update_status()

    def clone_into(self, other):
        other.family_only = self.family_only
        other.default_style = self.default_style
        other.setText(self.text())
        other.setStyleSheet(self.styleSheet())
        completions = self.completions.stringList()
        other.completions.setStringList(completions)
        other.completer.setCompletionPrefix(self.text())

    @property
    def _paths(self):
        return self.settings.get("packages_path")

    def _textEdited(self, txt):
        words = get_completions(txt,
                                paths=self._paths,
                                family_only=self.family_only)
        self.completions.setStringList(list(reversed(words)))

    def _set_style(self, style=None):
        if style is None:
            if self.default_style is not None:
                self.setStyleSheet(self.default_style)
        else:
            if self.default_style is None:
                self.default_style = self.styleSheet()
            self.setStyleSheet(style)

    def _update_status(self):
        def _ok():
            self._set_style()
            self.setToolTip("")

        def _err(msg, color="red"):
            self._set_style("QLineEdit { border : 2px solid %s;}" % color)
            self.setToolTip(msg)

        txt = str(self.text())
        if not txt:
            _ok()
            return

        try:
            req = Requirement(str(txt))
        except Exception as e:
            _err(str(e))
            return

        _ok()
        if not req.conflict:
            try:
                it = iter_packages(name=req.name,
                                   range=req.range,
                                   paths=self._paths)
                pkg = sorted(it, key=lambda x: x.version)[-1]
            except Exception:
                _err("cannot find package: %r" % txt, "orange")
                return

            if pkg.description:
                self.setToolTip(pkg.description)