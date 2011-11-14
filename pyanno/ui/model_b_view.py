# Copyright (c) 2011, Enthought, Ltd.
# Author: Pietro Berkes <pberkes@enthought.com>
# License: Modified BSD license (2-clause)
from enable.component_editor import ComponentEditor

from traits.has_traits import on_trait_change, HasTraits
from traits.trait_numeric import Array
from traits.trait_types import Instance, Str, Range, Button, Int, Any, Enum, List
from traitsui.editors.range_editor import RangeEditor
from traitsui.editors.tabular_editor import TabularEditor
from traitsui.group import VGroup, VGrid, HGroup, Group
from traitsui.include import Include
from traitsui.item import Item, Spring, UItem, Label
from traitsui.menu import OKButton
from traitsui.view import View

from pyanno.modelB import ModelB
from pyanno.plots.hinton_plot import HintonDiagramPlot
from pyanno.plots.matrix_plot import MatrixPlot
from pyanno.plots.theta_tensor_plot import ThetaTensorPlot
from pyanno.ui.arrayview import Array2DAdapter
from pyanno.ui.model_view import PyannoModelView, NewModelDialog
from pyanno.ui.parameters_tabular_viewer import ParametersTabularView

import numpy as np


WIDTH_CELL = 100
HEIGHT_CELL = 20
MAX_WIDTH = 800
MAX_HEIGHT = 800
W_MARGIN = 50
H_MARGIN = 250

MODEL_B_NAME = 'Model B (full model)'


class NewModelBDialog(NewModelDialog):
    """Create a dialog requesting the parameters to create Model B."""

    model_name = Str(MODEL_B_NAME)
    nclasses = Int(5)
    nannotators = Int(8)

    parameters_group = VGroup(
        Item(name='nclasses',
             editor=RangeEditor(mode='spinner', low=3, high=1000),
             label='Number of annotation classes:',
             width=100),
        Item(name='nannotators',
             editor=RangeEditor(mode='spinner', low=2, high=1000),
             label='Number of annotators:',
             width=100),
        group_theme = 'white_theme.png'
    )


class ModelB_MultipleThetaView(HasTraits):
    """Tabular view for the parameters theta in Model B.

    Includes a spin box to select the parameters for each annotator.
    """

    @classmethod
    def show(cls, theta):
        """Create a window that with a ThetaView inside."""
        tv = cls(theta=theta)
        tv.edit_traits()

    # 3D tensor to be displayed
    theta = Array

    # 4D tensor of samples (may be None if no samples available)
    theta_samples = Any

    # title of the view window
    title = "Model B, parameters theta"

    # annotator number
    annotator_idx = Int(0)

    # tabular view of theta for annotator j
    theta_j_view = Instance(HasTraits)

    def traits_view(self):

        traits_view = View(
            VGroup(
                Item('annotator_idx',
                     label='Annotator index',
                     editor=RangeEditor(mode='spinner',
                                        low=0, high=self.theta.shape[0]-1,
                                        ),
                ),
                VGroup(
                    Item('theta_j_view',
                         style='custom',
                         show_label=False)
                ),
            ),
            width = 500,
            height = 400,
            resizable = True
        )
        return traits_view


class ModelB_TabularThetaView(ModelB_MultipleThetaView):
    """Theta view is a tabular view."""

    def _theta_j_view_default(self):
        return ParametersTabularView(
            data = self.theta[self.annotator_idx,:,:].tolist()
        )

    @on_trait_change('annotator_idx')
    def _theta_j_update(self):
        self.theta_j_view.data = self.theta[self.annotator_idx,:,:].tolist()


class ModelB_MatrixThetaView(ModelB_MultipleThetaView):
    """Theta view is a matrix plot."""

    def _create_matrix_plot(self, annotator_idx):
        return MatrixPlot(
            matrix = self.theta[self.annotator_idx,:,:],
            colormap_low = 0., colormap_high = 1.,
            title = 'Theta[%d,:,:]' % self.annotator_idx
        )

    def _theta_j_view_default(self):
        return self._create_matrix_plot(self.annotator_idx)

    @on_trait_change('annotator_idx')
    def _theta_j_update(self):
        self.theta_j_view = self._create_matrix_plot(self.annotator_idx)


class ModelB_LineThetaView(ModelB_MultipleThetaView):
    """Theta view is a set of line plot."""

    def _create_line_plot(self, annotator_idx):
        samples = None
        if self.theta_samples is not None:
            samples = self.theta_samples[:,annotator_idx,:,:]
        plot_view = ThetaTensorPlot(
            theta = self.theta[annotator_idx,:,:],
            annotator_idx = annotator_idx,
            theta_samples = samples
        )
        return plot_view

    def _theta_j_view_default(self):
        return self._create_line_plot(self.annotator_idx)

    @on_trait_change('annotator_idx')
    def _theta_j_update(self):
        self.theta_j_view = self._create_line_plot(self.annotator_idx)


class ModelB_PriorView(HasTraits):
    """Show and allow to edit parameters"""

    @classmethod
    def show(cls, beta, alpha):
        """Create a window that with a ThetaView inside."""
        tv = cls(beta=beta[None,:], alpha=alpha)
        ui = tv.edit_traits(kind='modal')
        if ui.result:
            # user pressed 'OK'
            return tv.beta[0,:], tv.alpha
        else:
            return None, None

    beta = Array

    alpha = Array

    def traits_view(self):
        nclasses = self.beta.shape[1]
        w_table = WIDTH_CELL * nclasses
        h_table = HEIGHT_CELL * nclasses
        w_view = min(MAX_WIDTH, w_table + W_MARGIN)
        h_view = min(MAX_HEIGHT, h_table + HEIGHT_CELL + H_MARGIN)

        view = View(
            VGroup(
                Label('Beta parameters (prior over pi):'),
                UItem('beta',
                      editor=TabularEditor(
                          adapter=Array2DAdapter(ncolumns=nclasses,
                                                 format='%.4f',
                                                 show_index=True),
                          ),
                      width = w_table,
                      height = HEIGHT_CELL,
                      padding = 10
                ),
                Label('Alpha parameters (prior over theta):'),
                UItem('alpha',
                      editor=TabularEditor(
                          adapter=Array2DAdapter(ncolumns=nclasses,
                                                 format='%.4f',
                                                 show_index=True),
                          ),
                      width = w_table,
                      height = h_table,
                      padding = 10
                ),
                group_theme = 'white_theme.png'
            ),
            width = w_view,
            height = h_view,
            scrollable = True,
            resizable = True,
            buttons = ['OK', 'Cancel']
        )
        return view


class ModelBView(PyannoModelView):
    """ Traits UI Model/View for 'ModelB' objects.
    """

    # name of the model (inherited from PyannoModelView)
    model_name = MODEL_B_NAME

    # dialog to instantiated when creating a new model
    new_model_dialog_class = NewModelBDialog

    @classmethod
    def _create_model_from_dialog(cls, dialog):
        return ModelB.create_initial_state(dialog.nclasses, dialog.nannotators)


    @on_trait_change('model,model_updated')
    def update_from_model(self):
        """Update view parameters to the ones in the model."""
        self.pi_hinton_diagram = HintonDiagramPlot(
            data = self.model.pi.tolist(),
            title = 'Pi parameters, P(label=k)')

        self.theta_matrix_plot = ModelB_MatrixThetaView(theta=self.model.theta)

        self.theta_line_plot = ModelB_LineThetaView(theta=self.model.theta)

        self._theta_view_update()


    def plot_theta_samples(self, theta_samples):
        self.theta_line_plot = ModelB_LineThetaView(
            theta = self.model.theta,
            theta_samples = theta_samples
        )
        self._theta_view_update()


    #### UI traits

    pi_hinton_diagram = Instance(HintonDiagramPlot)

    theta_matrix_plot = Instance(ModelB_MatrixThetaView)

    theta_line_plot = Instance(ModelB_LineThetaView)

    theta_views = Enum('Line plot',
                       'Matrix plot (does not support samples)')

    theta_view = Instance(ModelB_MultipleThetaView)

    def _theta_view_default(self):
        return self.theta_line_plot

    @on_trait_change('theta_views')
    def _theta_view_update(self):
        if self.theta_views.startswith('Line'):
            self.theta_view = self.theta_line_plot
        else:
            self.theta_view = self.theta_matrix_plot


    #### Actions

    view_pi = Button(label='View Pi...')

    view_theta = Button(label='View Theta...')

    edit_prior = Button(label='Edit priors (Alpha, Beta)...')


    def _view_pi_fired(self):
        """Create viewer for parameters pi."""
        pi_view = ParametersTabularView(
            title = 'Model B, parameters Pi',
            data = [self.model.pi.tolist()]
        )
        pi_view.edit_traits()


    def _view_theta_fired(self):
        """Create viewer for parameters theta."""
        ModelB_TabularThetaView.show(self.model.theta)


    def _edit_prior_fired(self):
        """Create editor for prior parameters."""
        beta, alpha = ModelB_PriorView.show(beta=self.model.beta,
                                            alpha=self.model.alpha)
        if beta is not None:
            # user pressed 'OK'
            self.model.beta = beta
            self.model.alpha = alpha
            self.model_updated = True


    #### Traits UI view #########

    parameters_group = VGroup(
        Item('_'),

        HGroup(
            Item('handler.edit_prior',
                 show_label=False,
                 width=100),
            Spring(),
        ),

        Item('_'),

        HGroup(
            VGroup(
                Spring(),
                Item('handler.pi_hinton_diagram',
                     style='custom',
                     resizable=False,
                     show_label=False,
                     width=510),
                Spring(),
            ),
            Spring(),
            VGroup(
                Spring(),
                Item('handler.view_pi', show_label=False),
                Spring()
            ),
        ),

        Item('_'),

        HGroup(
            VGroup(
                Item('handler.theta_views',
                     show_label=False),
                Item('handler.theta_view',
                     style='custom',
                     resizable=False,
                     show_label=False,
                     width = 510),
                Spring()
            ),
            VGroup(
                Spring(),
                Item('handler.view_theta', show_label=False),
                Spring()
            )
        ),
    )

    body = VGroup(
        Include('info_group'),
        parameters_group
    )

    traits_view = View(body, buttons=[OKButton], resizable=True)


#### Testing and debugging ####################################################

def main():
    """ Entry point for standalone testing/debugging. """

    from pyanno import ModelB

    model = ModelB.create_initial_state(4, 5)
    anno = model.generate_annotations(100)
    samples = model.sample_posterior_over_accuracy(anno, 10)

    model_view = ModelBView(model=model)
    model_view.plot_theta_samples(samples)
    model_view.configure_traits(view='traits_view')

    return model, model_view


if __name__ == '__main__':
    m, mv = main()
