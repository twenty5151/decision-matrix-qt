import weakref
from functools import partial
from enum import IntEnum, auto

import numpy as np
from matrix import Matrix
from PySide2.QtCore import Qt
from PySide2.QtWidgets import (
    QWizard,
    QWizardPage,
    QRadioButton,
    QButtonGroup,
    QGridLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QSpinBox,
    QLabel,
    QSlider,
    QPushButton,
    QGroupBox,
    QVBoxLayout,
    QFormLayout,
    QHBoxLayout,
    QTableWidgetItem,
    QTableWidgetSelectionRange,
)

from gui.core import AbstractDataTab, AbstractValueScoreLayout


def clear_layout(layout):
    while (child := layout.takeAt(0)):
        del child


class Page(IntEnum):
    Welcome = auto()
    Choices = auto()
    Criteria = auto()
    Weights = auto()
    Continuous = auto()
    ContinuousWeights = auto()
    ValueScores = auto()
    Data = auto()
    Ratings = auto()
    Conclusion = auto()


class Wizard(QWizard):
    def __init__(self, parent):
        super(Wizard, self).__init__(parent.main_window)
        self.main_parent = parent
        self.setWindowTitle('Assistant')
        #self.setOption(QWizard.IndependentPages)
        self.setOption(QWizard.NoCancelButtonOnLastPage)

        self.next_button = QPushButton(self)
        self.next_button.clicked.connect(self.next)

        self.setButton(QWizard.CustomButton1, self.next_button)
        self.setOption(QWizard.HaveCustomButton1)
        self.setButtonText(QWizard.CustomButton1, '&Next >')
        self.setButtonLayout([
            QWizard.Stretch,
            QWizard.BackButton,
            QWizard.CustomButton1,
            QWizard.CancelButton,
            QWizard.FinishButton,
        ])

        self.setPage(Page.Welcome, WelcomePage(self))
        self.setPage(Page.Choices, ChoicesPage(self))
        self.setPage(Page.Criteria, CriteriaPage(self))
        self.setPage(Page.Weights, WeightsPage(self))
        self.setPage(Page.Continuous, ContinuousCriteriaPage(self))
        self.setPage(Page.ContinuousWeights, ContinuousCriteriaWeightsPage(self))
        self.setPage(Page.ValueScores, ValueScorePage(self))
        self.setPage(Page.Data, DataPage(self))
        self.setPage(Page.Ratings, RatingPage(self))
        self.setPage(Page.Conclusion, ConclusionPage(self))


class EnableNextOnBackMixin:
    def cleanupPage(self):
        self.parent_wizard.next_button.setEnabled(True)


class WelcomePage(QWizardPage):
    def __init__(self, parent):
        super(WelcomePage, self).__init__(parent)
        self.parent_wizard = weakref.proxy(parent)
        self.setTitle('Welcome')

        basic_radio = QRadioButton('&Basic')
        basic_radio.setChecked(True)
        self.advanced_radio = QRadioButton('&Advanced')

        group = QButtonGroup(self)
        group.addButton(basic_radio)
        group.addButton(self.advanced_radio)

        grid = QGridLayout(self)
        grid.addWidget(basic_radio, 0, 0)
        grid.addWidget(self.advanced_radio, 1, 0)

        self.registerField('basic', basic_radio)
        self.setLayout(grid)

    def initializePage(self):
        if self.parent_wizard.main_parent.matrix.continuous_criteria:
            self.advanced_radio.setChecked(True)


class AbstractMultiInputPage(EnableNextOnBackMixin, QWizardPage):
    def __init__(self, parent):
        QWizardPage.__init__(self, parent)
        self.parent_wizard = weakref.proxy(parent)

        self.label = QLabel()
        self.line_edit = QLineEdit()
        self.line_edit.returnPressed.connect(self.add_item)
        self.add_button = QPushButton()
        self.add_button.clicked.connect(self.add_item)

        self.list = QListWidget()
        self.delete_button = QPushButton('&Delete')
        self.delete_button.setDisabled(True)
        self.delete_button.clicked.connect(self.delete_item)

        grid = QGridLayout(self)
        grid.addWidget(self.label, 0, 0)
        grid.addWidget(self.line_edit, 0, 1)
        grid.addWidget(self.add_button, 0, 2)
        grid.addWidget(self.list, 1, 0, 1, 2)
        grid.addWidget(self.delete_button, 1, 2, 1, 1, Qt.AlignTop)

        self.setLayout(grid)

    def initializePage(self):
        if self.list.count() == 0:
            self.parent_wizard.next_button.setDisabled(True)

    def add_item(self):
        if not (name := self.line_edit.text()):
            return
        item = QListWidgetItem(name)
        self.list.addItem(item)
        self.matrix_add(name)
        self.line_edit.clear()
        self.line_edit.setFocus()
        self.parent_wizard.next_button.setEnabled(True)
        self.delete_button.setEnabled(True)

    def delete_item(self):
        if (index := self.list.currentRow()) is None or index == -1:
            return
        self.list.takeItem(index)
        self.matrix_remove(index)
        if self.list.count() == 0:
            self.delete_button.setDisabled(True)
            self.parent_wizard.next_button.setDisabled(True)

    def matrix_add(self, name):
        raise NotImplementedError

    def matrix_remove(self, index):
        raise NotImplementedError


class ChoicesPage(AbstractMultiInputPage):
    def __init__(self, parent):
        super().__init__(parent)
        self.setTitle('Choices')
        self.add_button.setText('&Add choice')
        self.label.setText('Choice name')
        # Add the choices
        # What are you trying to choose between?

    def initializePage(self):
        for choice in self.parent_wizard.main_parent.matrix.df.index[1:]:
            self.list.addItem(QListWidgetItem(choice))
        super().initializePage()

    def matrix_add(self, name):
        self.parent_wizard.main_parent.lineEdit.setText(name)
        self.parent_wizard.main_parent.add_row()

    def matrix_remove(self, index):
        idx = self.parent_wizard.main_parent.matrix.df.index[index + 1]  # Weight is first row
        self.parent_wizard.main_parent.matrix.df.drop(idx, inplace=True)
        self.parent_wizard.main_parent.matrix_widget.removeRow(index + 1)


class CriteriaPage(AbstractMultiInputPage):
    def __init__(self, parent):
        super().__init__(parent)
        self.setTitle('Criteria')
        self.add_button.setText('&Add criterion')
        self.label.setText('Criterion name')
        # Add the criteria
        # What characteristics does the choices have that matters?

    def initializePage(self):
        for criterion in self.parent_wizard.main_parent.matrix.criteria:
            self.list.addItem(QListWidgetItem(criterion))

        super().initializePage()

        if self.parent_wizard.main_parent.matrix.continuous_criteria:
            self.parent_wizard.next_button.setEnabled(True)

    def matrix_add(self, name):
        self.parent_wizard.main_parent.matrix.add_criterion(name, weight=np.nan)
        self.parent_wizard.main_parent.lineEdit.setText(name)
        self.parent_wizard.main_parent.add_column()

    def matrix_remove(self, index):
        idx = self.parent_wizard.main_parent.matrix.df.columns[index]
        self.parent_wizard.main_parent.matrix.df.drop(idx, axis='columns', inplace=True)
        self.parent_wizard.main_parent.matrix_widget.removeColumn(index)

    def nextId(self):
        if self.list.count() >= 1:
            return Page.Weights
        # Else, advanced mode is on
        return Page.Continuous


class ContinuousCriteriaPage(EnableNextOnBackMixin, QWizardPage):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent_wizard = weakref.proxy(parent)

        self.setTitle('Continuous criteria')
        # Radio button, if yes then ask for inputs
        self.yes = QRadioButton('&Yes, there are criteria that needs to be calculated')
        no = QRadioButton('N&o, I will manually give a rating for every choice and criteria')
        no.setChecked(True)

        self.registerField('yes', self.yes)
        self.yes.toggled.connect(self.toggled)

        group = QButtonGroup(self)
        group.addButton(self.yes)
        group.addButton(no)

        # Duplicated from AbstractMultiInputPage
        self.line_edit = QLineEdit()
        self.list_widget = QListWidget()
        self.add_button = QPushButton('&Add criterion')
        self.delete_button = QPushButton('&Delete')

        self.line_edit.setDisabled(True)
        self.list_widget.setDisabled(True)
        self.add_button.setDisabled(True)
        self.delete_button.setDisabled(True)

        self.line_edit.returnPressed.connect(self.add_item)
        self.add_button.clicked.connect(self.add_item)
        self.delete_button.clicked.connect(self.delete_item)

        grid = QGridLayout(self)
        grid.addWidget(self.yes, 0, 0)
        grid.addWidget(no, 1, 0)
        grid.addWidget(self.line_edit, 2, 0)
        grid.addWidget(self.add_button, 2, 1)
        grid.addWidget(self.list_widget, 3, 0)
        grid.addWidget(self.delete_button, 3, 1, Qt.AlignTop)
        self.setLayout(grid)

    def initializePage(self):
        for criterion in self.parent_wizard.main_parent.matrix.continuous_criteria:
            self.list_widget.addItem(QListWidgetItem(criterion))

        if self.list_widget.count() != 0:
            self.yes.setChecked(True)
            self.parent_wizard.next_button.setEnabled(True)

    def toggled(self, checked: bool):
        if checked:
            self.line_edit.setEnabled(True)
            self.list_widget.setEnabled(True)
            self.add_button.setEnabled(True)
            self.parent_wizard.next_button.setDisabled(True)
        else:
            self.line_edit.setDisabled(True)
            self.list_widget.setDisabled(True)
            self.parent_wizard.next_button.setEnabled(True)

    def add_item(self):
        # Duplicated
        if not (name := self.line_edit.text()):
            return
        item = QListWidgetItem(name)
        self.list_widget.addItem(item)
        self.line_edit.clear()
        self.line_edit.setFocus()
        self.parent_wizard.next_button.setEnabled(True)
        self.delete_button.setEnabled(True)

        self.parent_wizard.main_parent.line_edit_cc_tab.setText(name)
        self.parent_wizard.main_parent.matrix.add_continuous_criterion(
            name, weight=float('nan')
        )
        self.parent_wizard.main_parent.add_continuous_criteria()

    def delete_item(self):
        # Completely copied (except list -> list_widget)
        if (index := self.list_widget.currentRow()) is None or index == -1:
            return
        self.list_widget.takeItem(index)
        self.matrix_remove(index)
        if self.list_widget.count() == 0:
            self.delete_button.setDisabled(True)
            self.parent_wizard.next_button.setDisabled(True)

    def matrix_remove(self, index):
        idx = self.parent_wizard.main_parent.matrix.continuous_criteria.pop(index)
        self.parent_wizard.main_parent.matrix.df.drop(idx, axis='columns', inplace=True)
        self.parent_wizard.main_parent.matrix_widget.removeColumn(index)

        # FIXME: deleting item then adding it again doesn't add it in the tab
        # Remove the section in the value-score tab
        groupbox = self.parent_wizard.main_parent.cc_grid.takeAt(index + 1).widget()
        clear_layout(groupbox.layout())
        self.parent_wizard.main_parent.cc_grid.removeWidget(groupbox)
        groupbox.deleteLater()

    def nextId(self):
        if self.yes.isChecked():
            return Page.ContinuousWeights
        return Page.Ratings


class AbstractSliderPage(EnableNextOnBackMixin, QWizardPage):
    def __init__(self, parent):
        QWizardPage.__init__(self, parent)
        self.parent_wizard = weakref.proxy(parent)
        self.grid = QGridLayout(self)
        self.setLayout(self.grid)
        self.collection: 'func[] -> Iterable[str]'

    def initializePage(self):
        self.parent_wizard.next_button.setDisabled(True)
        self.sliders = []
        self.spin_boxes = []

        # FIXME: backing too much the returning breaks this
        # Seems to remember values, but visually breaks
        for i, name in enumerate(self.collection()):
            self.grid.addWidget(QLabel(str(name)), i, 0)

            spin_box = QSpinBox()
            spin_box.setRange(0, 10)
            cb = partial(self.spin_box_changed, i)
            spin_box.valueChanged.connect(cb)
            self.spin_boxes.append(spin_box)

            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setTickPosition(QSlider.TicksBelow)
            slider.setMaximum(10)
            slider.setPageStep(1)
            slider.setTracking(True)
            cb = partial(self.slider_changed, i)
            slider.valueChanged.connect(cb)
            self.sliders.append(slider)

            self.grid.addWidget(spin_box, i, 1)
            self.grid.addWidget(slider, i, 2)

        self.fix_tab_order()

        for idx, criterion in enumerate(self.collection()):
            value = self.parent_wizard.main_parent.matrix.df.loc['Weight', criterion]
            if str(value) != 'nan':
                self.spin_boxes[idx].setValue(value)

    def fix_tab_order(self):
        for box1, box2 in zip(self.spin_boxes, self.spin_boxes[1:]):
            self.setTabOrder(box1, box2)

        self.setTabOrder(self.spin_boxes[-1], self.sliders[0])

        for slider1, slider2 in zip(self.sliders, self.sliders[1:]):
            self.setTabOrder(slider1, slider2)

    def slider_changed(self, index, value):
        self.spin_boxes[index].setValue(value)
        self.parent_wizard.next_button.setEnabled(True)
        self.matrix_action(index, value)  # Only need to be triggered once

    def spin_box_changed(self, index, value):
        self.sliders[index].setValue(value)
        self.parent_wizard.next_button.setEnabled(True)

    def matrix_action(self, index, value):
        raise NotImplementedError


class WeightsPage(AbstractSliderPage):
    def __init__(self, parent):
        super().__init__(parent)
        self.collection = (
            lambda: self.parent_wizard.main_parent.matrix.criteria
        )
        self.setTitle('Weights')
        # Assign weights to your criteria
        # Rate their relative importance

    def matrix_action(self, index, value):
        self.parent_wizard.main_parent.matrix.df.iloc[0, index] = value
        self.parent_wizard.main_parent.matrix_widget.setItem(
            0, index, QTableWidgetItem(str(value))
        )

    def nextId(self):
        if self.field('basic'):
            return Page.Ratings
        return Page.Continuous


class ContinuousCriteriaWeightsPage(AbstractSliderPage):
    def __init__(self, parent):
        super().__init__(parent)
        self.collection = lambda: self.parent_wizard.main_parent.matrix.continuous_criteria
        self.setTitle('Continuous criteria weights')

    def matrix_action(self, index, value):
        criterion = self.parent_wizard.main_parent.matrix.continuous_criteria[index]
        self.parent_wizard.main_parent.matrix.df.loc['Weight', criterion] = value
        col = index + len(list(self.parent_wizard.main_parent.matrix.criteria))
        self.parent_wizard.main_parent.matrix_widget.setItem(
            0, col, QTableWidgetItem(str(value))
        )


class RatingPage(EnableNextOnBackMixin, QWizardPage):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent_wizard = weakref.proxy(parent)
        self.setTitle('Ratings')
        self.grid = QGridLayout(self)
        self.setLayout(self.grid)
        self.spin_boxes: dict[str, list[QSpinBox]] = {}
        self.sliders: dict[str, list[QSlider]] = {}

    def initializePage(self):
        self.parent_wizard.next_button.setDisabled(True)
        # grid
        # |----> groupbox 1 (for choice 1)
        #        |----> vertical_layout 1
        #               |----> inner_grid 1 (for criteria 1)
        #                      |----> label1
        #                      |----> value_spin_box 1
        #               |----> inner_grid 2 (for criteria 2)
        #                      |----> label2
        #                      |----> rating_spin_box 2
        # |----> groupbox 2 (for choice 2)
        #        |-...
        # TODO: consider extracting out common code with
        # AbstractSliderPage
        for choice in self.parent_wizard.main_parent.matrix.df.index[1:]:
            groupbox = QGroupBox(choice)
            vertical_layout = QVBoxLayout(groupbox)
            self.grid.addWidget(groupbox)
            self.spin_boxes[choice] = []
            self.sliders[choice] = []

            for row, criterion in enumerate(self.parent_wizard.main_parent.matrix.criteria):
                rating_spin_box = QSpinBox()
                rating_spin_box.setRange(0, 10)
                self.spin_boxes[choice].append(rating_spin_box)

                slider = QSlider(Qt.Orientation.Horizontal)
                slider.setTickPosition(QSlider.TicksBelow)
                slider.setMaximum(10)
                slider.setPageStep(1)
                slider.setTracking(True)
                self.sliders[choice].append(slider)

                cb = partial(self.spin_box_changed, row, choice, criterion)
                rating_spin_box.valueChanged.connect(cb)

                cb = partial(self.slider_changed, row, choice, criterion)
                slider.valueChanged.connect(cb)

                spin_box_and_slider = QHBoxLayout()
                spin_box_and_slider.addWidget(rating_spin_box)
                spin_box_and_slider.addWidget(slider)

                inner_form = QFormLayout()
                inner_form.addRow(QLabel(criterion), spin_box_and_slider)
                vertical_layout.addLayout(inner_form)

    def slider_changed(self, row, choice, criterion, value):
        self.spin_boxes[choice][row].setValue(value)
        self.parent_wizard.next_button.setEnabled(True)
        self.value_changed(choice, criterion, value)  # Only need to be triggered once

    def spin_box_changed(self, row, choice, criterion, value):
        self.sliders[choice][row].setValue(value)
        self.parent_wizard.next_button.setEnabled(True)

    def value_changed(self, choice, criterion, value):
        self.parent_wizard.main_parent.matrix.rate_choices({choice: {criterion: value}})
        self.parent_wizard.next_button.setEnabled(True)
        item = QTableWidgetItem(str(value))
        row = self.parent_wizard.main_parent.matrix.df.index.get_loc(choice)
        col = self.parent_wizard.main_parent.matrix.df.columns.get_loc(criterion)
        self.parent_wizard.main_parent.matrix_widget.setItem(row, col, item)


class ValueScorePage(EnableNextOnBackMixin, AbstractValueScoreLayout, QWizardPage):
    def __init__(self, parent):
        QWizardPage.__init__(self, parent)
        AbstractValueScoreLayout.__init__(self, QGridLayout(self))
        self.parent_wizard = weakref.proxy(parent)
        self.matrix = self.parent_wizard.main_parent.matrix
        self.tab_1 = self.parent_wizard.main_parent.matrix_tab
        self.setTitle('Criterion value to scores')

    def initializePage(self):
        self.parent_wizard.next_button.setDisabled(True)
        super().initializePage(self.matrix.continuous_criteria)

    def value_changed(self, criterion, index, value):
        if self.has_score:
            self.parent_wizard.next_button.setEnabled(True)
        super().value_changed(criterion, index, value)
        (self.parent_wizard.main_parent
            .cc_tab_page.value_spin_boxes[criterion][index].setValue(value))

    def score_changed(self, criterion, index, score):
        if self.has_value:
            self.parent_wizard.next_button.setEnabled(True)
        super().score_changed(criterion, index, score)
        (self.parent_wizard.main_parent
            .cc_tab_page.score_spin_boxes[criterion][index].setValue(score))

    def nextId(self):
        # If the only criteria that exist is continuous, skip the ratings page
        if (
            not list(self.parent_wizard.main_parent.matrix.criteria)
            and self.parent_wizard.main_parent.matrix.continuous_criteria
        ):
            return Page.Conclusion
        #return Page.Ratings
        return super().nextId()


class DataPage(EnableNextOnBackMixin, AbstractDataTab, QWizardPage):
    def __init__(self, parent):
        QWizardPage.__init__(self, parent)
        AbstractDataTab.__init__(self)
        self.parent_wizard = weakref.proxy(parent)
        self.grid = QVBoxLayout(self)
        self.setTitle('Data')
        self.matrix = self.parent_wizard.main_parent.matrix

    def initializePage(self):
        for choice in self.matrix.df.index[1:]:
            # Every choice gets a groupbox
            groupbox = QGroupBox(choice)
            QVBoxLayout(groupbox)
            for criterion in self.matrix.continuous_criteria:
                inner_grid = QHBoxLayout()
                self.add_row(inner_grid, choice, criterion)
                groupbox.layout().addLayout(inner_grid)
                self.grid.addWidget(groupbox)

    def sync(self, choice, criterion, value):
        (self.parent_wizard.main_parent.data_tab_page
                .spin_boxes[choice][criterion].setValue(value))


class ConclusionPage(QWizardPage):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent_wizard = weakref.proxy(parent)
        self.setTitle('All done!')
        self.setFinalPage(True)

    def initializePage(self):
        self.parent_wizard.setButtonLayout([
            QWizard.Stretch,
            QWizard.BackButton,
            QWizard.CancelButton,
            QWizard.FinishButton,
        ])

    def cleanupPage(self):
        self.parent_wizard.next_button.setEnabled(True)
        self.parent_wizard.setButtonLayout([
            QWizard.Stretch,
            QWizard.BackButton,
            QWizard.CustomButton1,
            QWizard.CancelButton,
            QWizard.FinishButton,
        ])


class WizardMixin:
    def init_wizard(self):
        self.wizard = Wizard(self)
        self.wizard.rejected.connect(self.rejected)
        self.wizard.show()

    def rejected(self):
        #self.matrix = Matrix()
        #print(self.matrix)
        pass
