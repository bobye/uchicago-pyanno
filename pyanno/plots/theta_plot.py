# Copyright (c) 2011, Enthought, Ltd.
# Author: Pietro Berkes <pberkes@enthought.com>
# License: Apache license

"""TraitsUI view of the Theta parameters, and their samples."""

from chaco.array_plot_data import ArrayPlotData
from chaco.data_range_2d import DataRange2D
from chaco.label_axis import LabelAxis
from chaco.plot import Plot
from chaco.scales.scales import FixedScale
from chaco.scales_tick_generator import ScalesTickGenerator
from enable.component_editor import ComponentEditor

from traits.has_traits import on_trait_change
from traits.trait_numeric import Array
from traits.trait_types import Instance, Bool, Event, Str, DictStrAny
from traitsui.item import Item

import numpy as np
from pyanno.plots.plots_superclass import PyannoPlotContainer


def _w_idx(str_, idx):
    """Append number to string. Used to generate PlotData labels"""
    return str_ + str(idx)


class ThetaPlot(PyannoPlotContainer):
    """Defines a view of the annotator accuracy parameters, theta.

    The view consists in a Chaco plot that displays the theta parameter for
    each annotator, and samples from the posterior distribution over theta
    with a combination of a scatter plot and a candle plot.
    """

    #### Traits definition ####################################################

    theta_samples_valid = Bool(False)
    theta_samples = Array(dtype=float, shape=(None, None))

    # return value for "Copy" action on plot
    data = DictStrAny

    @on_trait_change('theta_samples,theta_samples_valid')
    def _update_data(self):
        if not self.data.has_key('theta'):
            self.data = {'theta': None, 'theta_samples': None}

        if self.theta_samples_valid:
            theta_samples = self.theta_samples.tolist()
        else:
            theta_samples = None

        self.data['theta'] = self.model.theta.tolist()
        self.data['theta_samples'] = theta_samples.tolist()

    #### plot-related traits
    title = Str('Accuracy of annotators (theta)')

    theta_plot_data = Instance(ArrayPlotData)
    theta_plot = Instance(Plot)

    redraw = Event


    ### Plot definition #######################################################

    def _compute_range2d(self):
        low = min(0.6, self.model.theta.min()-0.05)
        if self.theta_samples_valid:
            low = min(low, self.theta_samples.min()-0.05)
        range2d = DataRange2D(low=(0., low),
                              high=(self.model.theta.shape[0]+1, 1.))
        return range2d


    @on_trait_change('model:theta,theta_samples,theta_samples_valid',
                     post_init=True)
    def _update_range2d(self):
        self.theta_plot.range2d = self._compute_range2d()


    def _theta_plot_default(self):
        """Create plot of theta parameters."""

        # We plot both the thetas and the samples from the posterior; if the
        # latter are not defined, the corresponding ArrayPlotData names
        # should be set to an empty list, so that they are not displayed
        theta = self.model.theta
        theta_len = theta.shape[0]

        # create the plot data
        if not self.theta_plot_data:
            self.theta_plot_data = ArrayPlotData()
            self._update_plot_data()

        # create the plot
        theta_plot = Plot(self.theta_plot_data)

        for idx in range(theta_len):
            # candle plot summarizing samples over the posterior
            theta_plot.candle_plot((_w_idx('index', idx),
                                    _w_idx('min', idx),
                                    _w_idx('barmin', idx),
                                    _w_idx('avg', idx),
                                    _w_idx('barmax', idx),
                                    _w_idx('max', idx)),
                                    color = "lightgray",
                                    bar_line_color = "black",
                                    stem_color = "blue",
                                    center_color = "red",
                                    center_width = 2)

            # plot of raw samples
            theta_plot.plot((_w_idx('ysamples', idx),
                             _w_idx('xsamples', idx)),
                            type='scatter',
                            color='red',
                            marker='plus',
                            line_width=1,
                            marker_size=3)

            # plot current parameters
            theta_plot.plot((_w_idx('y', idx), _w_idx('x', idx)),
                            type='scatter',
                            color='black',
                            marker='plus',
                            marker_size=8,
                            line_width=2)

        # adjust axis bounds
        theta_plot.range2d = self._compute_range2d()

        # remove horizontal grid and axis
        theta_plot.underlays = [theta_plot.x_grid, theta_plot.y_axis]

        # create new vertical axis
        label_list = [str(i) for i in range(1, theta_len+1)]

        label_axis = LabelAxis(
            theta_plot,
            orientation = 'bottom',
            positions = range(1, theta_len+1),
            labels = label_list,
            label_rotation = 0
        )
        # use a FixedScale tick generator with a resolution of 1
        label_axis.tick_generator = ScalesTickGenerator(scale=FixedScale(1.))

        theta_plot.index_axis = label_axis
        theta_plot.underlays.append(label_axis)
        #theta_plot.padding_bottom = 15

        self.decorate_plot(theta_plot, self.data)
        return theta_plot


    ### Handle plot data ######################################################

    def _samples_names_and_values(self, idx):
        """Return a list of names and values for the samples PlotData."""

        # In the following code, we rely on lazy evaluation of the
        # X if CONDITION else Y statements to return a default value if the
        # theta samples are not currently defined, or the real value if they
        # are.

        invalid = not self.theta_samples_valid
        samples = [] if invalid else np.sort(self.theta_samples[:,idx])
        nsamples = None if invalid else samples.shape[0]
        perc5 = None if invalid else samples[int(nsamples*0.05)]
        perc95 = None if invalid else samples[int(nsamples*0.95)]

        data_dict = {
            'xsamples':
                [] if invalid else samples,
            'ysamples':
                [] if invalid else np.zeros((nsamples,)) + idx + 1.2,
            'min':
                [] if invalid else [perc5],
            'max':
                [] if invalid else [perc95],
            'barmin':
                [] if invalid else [samples.mean() - samples.std()],
            'barmax':
                [] if invalid else [samples.mean() + samples.std()],
            'avg':
                [] if invalid else [samples.mean()],
            'index':
                [] if invalid else [idx + 0.8]
        }

        name_value = [(_w_idx(name, idx), value)
                      for name, value in data_dict.items()]
        return name_value

    @on_trait_change('theta_plot_data,theta_samples_valid,redraw')
    def _update_plot_data(self):
        """Updates PlotData on changes."""
        theta = self.model.theta

        plot_data = self.theta_plot_data

        for idx, th in enumerate(theta):
            #
            plot_data.set_data('x%d' % idx, [th])
            plot_data.set_data('y%d' % idx, [idx+1.2])

            for name_value in self._samples_names_and_values(idx):
                name, value = name_value
                plot_data.set_data(name, value)


    #### View definition #####################################################

    resizable_plot_item = Item(
        'theta_plot',
        editor=ComponentEditor(),
        resizable=True,
        show_label=False,
        width=600,
        height=400
        )

    traits_plot_item = Item(
        'theta_plot',
        editor=ComponentEditor(),
        resizable=True,
        show_label=False,
        width=-300,
        height=-300
        )


def plot_theta_parameters(modelBt, theta_samples=None, **kwargs):
    """Display a Chaco plot of of the annotator accuracy parameters, theta.

    The component allows saving the plot (with Ctrl-S), and copying the matrix
    data to the clipboard (with Ctrl-C).

    Input:
    modelBt -- an instance of ModelBt
    theta_samples -- if given, samples from the posterior over theta,
        as returned by modelBt.sample_posterior_over_theta

    Keyword arguments:
    title -- title for the resulting plot
    """

    theta_view = ThetaPlot(model=modelBt, **kwargs)
    if theta_samples is not None:
        theta_view.theta_samples = theta_samples
        theta_view.theta_samples_valid = True
    theta_view.configure_traits(view='resizable_view')
    return theta_view


#### Testing and debugging ####################################################

def main():
    """ Entry point for standalone testing/debugging. """

    from pyanno import ModelBt

    model = ModelBt.create_initial_state(5)
    annotations = model.generate_annotations(model.generate_labels(100))
    theta_samples = model.sample_posterior_over_theta(annotations, 100,
                                                      step_optimization_nsamples=3)

    theta_view = plot_theta_parameters(model, theta_samples,
                                       title='Debug plot_theta_parameters')

    return model, theta_view


if __name__ == '__main__':
    model, theta_view = main()