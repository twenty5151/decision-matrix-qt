import pytest
import numpy as np
from PySide2.QtCore import Qt
from unittest.mock import Mock, call

from matrix import Matrix

from gui import wizard


def new_subscriptable_mock():
    class SubscriptableMock(Mock):
        subscripts = []
        set_items = {}

        def __getitem__(self, other):
            self.subscripts.append(other)
            return self

        def __setitem__(self, item, value):
            self.set_items[item] = value
            return self

    return SubscriptableMock()


def abstract_multi_input_page_tester(qtbot, w, text1, text2):
    qtbot.keyClicks(w.currentPage().line_edit, text1)
    assert w.currentPage().line_edit.text() == text1

    qtbot.keyClick(w.currentPage().line_edit, Qt.Key_Enter)
    assert w.currentPage().line_edit.text() == ''
    assert w.currentPage().list.item(0).text() == text1

    qtbot.keyClicks(w.currentPage().line_edit, text2)
    qtbot.mouseClick(w.currentPage().add_button, Qt.LeftButton)
    assert w.currentPage().line_edit.text() == ''
    assert w.currentPage().list.item(1).text() == text2
    assert w.currentPage().list.count() == 2

    w.currentPage().list.setCurrentRow(1)
    qtbot.mouseClick(w.currentPage().delete_button, Qt.LeftButton)
    assert w.currentPage().list.count() == 1
    assert w.currentPage().list.item(0).text() == text1


def test_choices_wizard_page(qtbot):
    w = wizard.Wizard()
    matrix = new_subscriptable_mock()
    w.matrix = matrix
    qtbot.addWidget(w)
    w.show()

    # Setup
    qtbot.mouseClick(w.next_button, Qt.LeftButton)
    assert type(w.currentPage()) == wizard.ChoicesPage

    # Test page
    abstract_multi_input_page_tester(qtbot, w, 'apple', 'orange')

    assert len(w.matrix.method_calls) == 3
    assert w.matrix.method_calls[:-1] == [
        call.add_choices('apple'),
        call.add_choices('orange'),
        #call.df.drop(<SubscriptableMock>, inplace=True),
    ]
    assert w.matrix.method_calls[-1][0] == 'df.drop'
    # The first argument is a <SubscriptableMock> here
    assert w.matrix.method_calls[-1][2] == {'inplace': True}


def test_criteria_wizard_page(qtbot):
    w = wizard.Wizard()
    matrix = new_subscriptable_mock()
    w.matrix = matrix
    qtbot.addWidget(w)
    w.show()

    # Setup
    qtbot.mouseClick(w.next_button, Qt.LeftButton)
    qtbot.keyClicks(w.currentPage().line_edit, 'apple')
    qtbot.keyClick(w.currentPage().line_edit, Qt.Key_Enter)
    qtbot.mouseClick(w.next_button, Qt.LeftButton)
    assert type(w.currentPage()) == wizard.CriteriaPage

    # Test page
    abstract_multi_input_page_tester(qtbot, w, 'taste', 'size')

    assert len(w.matrix.method_calls) == 4
    assert w.matrix.method_calls[:-1] == [
        call.add_choices('apple'),

        call.add_criterion('taste', weight=np.nan),
        call.add_criterion('size', weight=np.nan),
        #call.df.drop(None, axis='columns', inplace=True),
    ]
    assert w.matrix.method_calls[-1][0] == 'df.drop'
    # The first argument is a <SubscriptableMock> here
    assert w.matrix.method_calls[-1][2] == {'axis': 'columns', 'inplace': True}


def test_weights_wizard_page_basic(qtbot):
    w = wizard.Wizard()
    w.page(wizard.Page.Weights).collection = lambda: ['size', 'taste']
    matrix = new_subscriptable_mock()
    w.matrix = matrix
    qtbot.addWidget(w)
    w.show()

    # Setup
    qtbot.mouseClick(w.next_button, Qt.LeftButton)
    qtbot.keyClicks(w.currentPage().line_edit, 'apple')
    qtbot.keyClick(w.currentPage().line_edit, Qt.Key_Enter)
    qtbot.mouseClick(w.next_button, Qt.LeftButton)
    qtbot.keyClicks(w.currentPage().line_edit, 'size')
    qtbot.keyClick(w.currentPage().line_edit, Qt.Key_Enter)
    qtbot.keyClicks(w.currentPage().line_edit, 'taste')
    qtbot.keyClick(w.currentPage().line_edit, Qt.Key_Enter)
    qtbot.mouseClick(w.next_button, Qt.LeftButton)
    assert type(w.currentPage()) == wizard.WeightsPage

    # Test page
    assert len(w.currentPage().sliders) == 2
    assert len(w.currentPage().spin_boxes) == 2

    # Spin boxes and sliders have synchronized values
    w.currentPage().spin_boxes[0].setValue(3)
    assert w.currentPage().spin_boxes[0].value() == w.currentPage().sliders[0].value() == 3
    w.currentPage().spin_boxes[1].setValue(7)
    assert w.currentPage().spin_boxes[1].value() == w.currentPage().sliders[1].value() == 7

    # Using up-arrow key to change value
    qtbot.mouseClick(w.currentPage().spin_boxes[0], Qt.LeftButton)
    qtbot.keyClick(w.currentPage().spin_boxes[0], Qt.Key_Up)
    assert w.currentPage().spin_boxes[0].value() == w.currentPage().sliders[0].value() == 4

    assert matrix.subscripts == ['Weight'] * 3
    assert matrix.set_items == {0: 4, 1: 7}


def test_ratings_basic(qtbot):
    w = wizard.Wizard()
    w.page(wizard.Page.Weights).collection = lambda: ['size', 'taste']
    w.matrix = Matrix()
    qtbot.addWidget(w)
    w.show()

    # Setup
    qtbot.mouseClick(w.next_button, Qt.LeftButton)
    qtbot.keyClicks(w.currentPage().line_edit, 'apple')
    qtbot.keyClick(w.currentPage().line_edit, Qt.Key_Enter)
    qtbot.keyClicks(w.currentPage().line_edit, 'orange')
    qtbot.keyClick(w.currentPage().line_edit, Qt.Key_Enter)
    qtbot.mouseClick(w.next_button, Qt.LeftButton)
    qtbot.keyClicks(w.currentPage().line_edit, 'size')
    qtbot.keyClick(w.currentPage().line_edit, Qt.Key_Enter)
    qtbot.keyClicks(w.currentPage().line_edit, 'taste')
    qtbot.keyClick(w.currentPage().line_edit, Qt.Key_Enter)
    qtbot.mouseClick(w.next_button, Qt.LeftButton)
    w.currentPage().spin_boxes[0].setValue(4)
    w.currentPage().spin_boxes[1].setValue(7)
    qtbot.mouseClick(w.next_button, Qt.LeftButton)
    assert type(w.currentPage()) == wizard.RatingPage

    # Test page
    number_of_choices = 2
    assert len(w.currentPage().sliders.keys()) == number_of_choices
    assert len(w.currentPage().spin_boxes.keys()) == number_of_choices

    number_of_criteria = 2
    for choice in ('apple', 'orange'):
        assert len(w.currentPage().sliders[choice]) == number_of_criteria
        assert len(w.currentPage().spin_boxes[choice]) == number_of_criteria

    for choice in ('apple', 'orange'):
        for row in (0, 1):
            w.currentPage().spin_boxes[choice][row].setValue(5)
            # Spin boxes and sliders have synchronized values
            assert (
                w.currentPage().spin_boxes[choice][row].value()
                == w.currentPage().sliders[choice][row].value()
                == 5
            )

            # Using up-arrow key to change value
            qtbot.mouseClick(w.currentPage().spin_boxes[choice][row], Qt.LeftButton)
            qtbot.keyClick(w.currentPage().spin_boxes[choice][row], Qt.Key_Up)
            assert (
                w.currentPage().spin_boxes[choice][row].value()
                == w.currentPage().sliders[choice][row].value()
                == 6
            )

    # First value is empty
    assert (w.matrix.df.loc['Weight'][:-1] == [4, 7]).all()
    assert (w.matrix.df.loc[:, 'Percentage'][1:] == [60, 60]).all()

    w.currentPage().spin_boxes['apple'][0].setValue(3)
    assert w.matrix.df.loc[:, 'Percentage'][1] == 49.09090909090909

    w.currentPage().spin_boxes['apple'][1].setValue(7)
    assert w.matrix.df.loc[:, 'Percentage'][1] == 55.45454545454545

    w.currentPage().spin_boxes['orange'][0].setValue(4)
    assert w.matrix.df.loc[:, 'Percentage'][2] == 52.72727272727272

    w.currentPage().spin_boxes['orange'][1].setValue(7)
    assert w.matrix.df.loc[:, 'Percentage'][2] == 59.09090909090909
