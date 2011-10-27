#!/usr/bin/env python
"""
  estimates model parameters under models A and Bt

  *modelnumber*  -- 1 for model A,
                    2 for Bt
  *numberOfRuns* -- number of independent runs with a randomly
                    chosen starting point in parameter space
  *usepriors* -- 1 or 0; if set to 1, uses beta-priors for
                    theta-parameters with (a,b) set to (2,1)
  *estimatealphas* -- 1 or 0; if set to 1, alpha-parameters are used
                    explicitly in the likelihood function
                    (to get proper ML or MAP estimates, in the text
                    the model is described as A-with-Alphas); if set to 0,
                    alpha-parameters are computed as a function of
                    estimates of omega-parameters
    *useomegas* -- 1 or 0 (use or don't estimated code frequencies in
                    initializing gamma-parameters of model Bt)


  *dim* -- total number of admissible annotation values

 shared service functions:

                        *check_data*
                        *compute_counts*
                        *format_posteriors*
                        *string_wrap*
                        *print_wrap*
                        *array_format*
                        *unique*
                        *num2comma*

    *Reference to the modeling details:*

    Rzhetsky A, Shatkay H, Wilbur WJ (2009)
    How to Get the Most out of Your Curation Effort.
    PLoS Comput Biol 5(5): e1000391.
    doi:10.1371/journal.pcbi.1000391
"""

from numpy import *
import numpy as np
import scipy as sp
from scipy import *
from pylab import *
import time
import shelve
import scipy.optimize
import scipy.stats
from time import strftime
from matplotlib import *
from enthought.traits.api import HasTraits, Str, Int, Range, Bool,\
    Array, Enum, Dict, File, on_trait_change, Button
from enthought.traits.ui.api import View, Item, Group, Handler
from enthought.traits.ui.menu import CancelButton, ApplyButton, Action
from pyanno.modelA import ModelA

from pyanno.modelBt import ModelBt
from pyanno.util import compute_counts, string_wrap


# FIXME refactoring breaks the loading of best results over multiple runs


#==========================================================
#==========================================================
#              Service functions
#------ compute unique list:  --------------------------
def unique(seq, keepstr=True):
    se = set(seq)
    s = list(se)
    return s


#-------------------------------------------------------------
def num2comma(num):
    if num == Inf:
        return "Infinity"
    elif num == -Inf:
        return "-Infinity"
    elif num == 0:
        return "0"

    order = log10(num)
    if (order / 3) > int(order / 3):
        groups = int(order / 3 + 1)
    else:
        groups = int(order / 3)

    x = zeros(groups)
    prev = num
    s = ""
    for i in range(groups):
        x[i] = int(prev / 10 ** (3 * (groups - i - 1)))
        prev -= int(x[i] * 10 ** (3 * (groups - i - 1)))
        if i < groups - 1:
            s += str(int(x[i])) + ","
        else:
            s += str(int(x[i]))

    return s


#----------------------------------------------------------
def format_posteriors(mat, alphas, dimension, thetas, gam, modelnumber,
                      model):
    mat = array(mat)
    posteriors = model.infer_labels(mat)

    return posteriors


#----------------------------------------------------------



#----------------------------------------------------------
def print_wrap(st):
    print "\033[01;34m" + str(st) + "\033[0m"
    return 0


#----------------------------------------------------------
def array_format(arr, format):
    s = ""
    for a in arr:
        s += str(format % a)
    return s


#----------------------------------------------------------
def read_labels(filein):
    annotators = []
    codes = []

    if not os.path.isfile(filein):
        print "Label definition file <" + filein + "> does not exist!!!"
        return annotators, codes

    for line in open(filein):
        if not line:
            break
        elif line.strip() == "":
            continue

        line = line.strip()

        if cmp(line, 'ANNOTATORS:') == 0:
            tmplist = annotators
        elif cmp(line, 'CODES:') == 0:
            tmplist = codes
        else:
            tmplist.append(line)

    return annotators, codes


#-------------------------------------------------------------
def check_data(filename, optional_labels, report):
    """
    Output
    mat -- array of annotations (integer array, nitems x 8)
    dim -- number of distinct annotation values
    values -- list of possible annotation values (same as in file - 1
    imap -- value-to-index map
    originaldata -- same as mat, without subtracting 1
    annotators -- ??? (from read_labels)
    codes -- ??? (from read_labels)
    n -- number of annotations
    """
    n = 0

    # TODO use numpy loadtxt
    # open file a first time to check consistency
    a = zeros(8)
    for line in open(filename):
        if not line:
            break
        elif line.strip() == "":
            continue
        n += 1
        j = 0
        for word in line.split():
            a[j] = int(word.replace(',', '').strip())
            j += 1

        if j != 8:
            print "Line #" + str(n) + " is ill-formed: " + str(j)
            print line

    if cmp(report, 'Nothing') != 0:
        print string_wrap(num2comma(n) + " lines in file " + filename + '...',
                          1)

    # open file a second time and read the data
    aa = zeros([n, 8], int)
    i = 0
    for line in open(filename):
        if not line:
            break
        elif line.strip() == "":
            continue

        j = 0
        for word in line.split():
            aa[i, j] = int(word.replace(',', '').strip())
            j += 1
        i += 1

    # Try to read labels
    annotators = None
    codes = None
    if optional_labels is not None:
        annotators, codes = read_labels(optional_labels)

    # Creating image
    #====================================================
    m, dd, ii = plot_annotators(aa, annotators, n, filename)
    #====================================================

    #----------------------------
    # create list of annotation values
    values = sp.zeros(m, int)
    j = 0
    for i in range(len(ii)):
        if ii[i] >= 0:
            values[j] = int(ii[i]) - 1
            j += 1

    # values of annotations have to be integer and positive
    # imap is a value --> to index map
    mm = sp.amax(values)
    imap = sp.zeros(mm + 1, int)
    # ??? I think this is broken: it should be imap[values[i]] = i
    for i in range(m):
        imap[values[i] - 1] = i

    if cmp(report, 'Nothing') != 0:
        print " "

    # data: make sure that -1 stands for no annotation
    # the rest of codes orea 0 to dim-1
    mat = sp.zeros([n, 8], int)

    for i in range(n):
        for j in range(8):
            if aa[i, j] > 0:
                mat[i, j] = aa[i, j] - 1
            else:
                mat[i, j] = aa[i, j]

    return mat, m, values, imap, aa, annotators, codes, n


#------------------------------------------------------
def plot_annotators(aa, annotators, n, filename):
    pyplot.figure(num=None, dpi=100, facecolor='w', edgecolor='k')
    hold(True)
    xlabel('Annotators')
    ylabel('Units of annotation')

    bb = zeros([n, 8])

    for i in range(n):
        for j in range(8):
            if aa[i, j] >= 0:
                bb[i, j] = 1
            else:
                bb[i, j] = 0

    cc = [0]
    k = 0

    for i in range(1, n):
        l = 0
        for j in range(8):
            if bb[i, j] != bb[cc[k], j] and l == 0:
                cc.append(i)
                k += 1
                l = 1

    l = 0
    dd = zeros([k + 1, 8])
    for i in range(k + 1):
        for j in range(8):
            dd[i, j] = 1 - bb[cc[i], j]
    spy(dd)
    hot()
    # plot

    # dimension is the number of distinct values excluding "-1" (no value)

    ee = list(aa.flatten(1))
    ii = unique(ee)  # list of annotations values(including -1)
    m = len(ii) - 1  # number of distinct values for annotations

    title(filename + ": " + str(m) + ' distinct annotation values')

    tty = []
    for i in range(k + 1):
        tty.append(num2comma(cc[i]))

    tty.append(num2comma(n))

    yticks(arange(k + 2) - 0.5, tty)

    if annotators is None:
        ttx = []
        for i in range(8):
            ttx.append(str(i + 1))
    else:
        ttx = annotators

    xticks(arange(8), ttx)
    show()
    return m, dd, ii


def form_filename(oldf, suffix):
    fi = oldf.split('.')
    fileout = fi[0] + suffix
    return fileout






#------------------------------------------------------------------------------------------
#==========================================================================================
def analyse_parameter_distribution(values, confidence, nbs):
    alpha = (1. - confidence) / 2.
    nn, bins = histogram(values, bins=nbs, range=None, normed=False,
                         weights=None)
    binsize = bins[1] - bins[0]
    binmin = bins[0]
    n = len(nn)
    x = zeros(n, float)
    y = zeros(n, float)
    x[0] = binmin + binsize / 2
    sn = sum(nn)

    vmean = numpy.mean(values, axis=0)
    vmode = scipy.stats.mode(values, axis=0)[0][0]
    vmedian = numpy.median(values, axis=0)
    vskew = scipy.stats.skew(values, axis=0)
    vstd = numpy.std(values, axis=0)


    #  vtable = freqtable(values,axis=0)

    #  print vmean, vmode, vmedian, vskew, 2*vstd

    for i in range(n):
        y[i] = float(nn[i] / (1. * sn))
    for i in range(1, n):
        x[i] = x[i - 1] + binsize

    vs = sort(values)
    nm = len(values)

    n1 = int(nm * alpha)
    n2 = int(nm * (1. - alpha))
    x_left = vs[n1]
    x_right = vs[n2]

    if vmode < x_left or vmode > x_right:
        print 'Mode is outside two-sided CI. Skewed distribution!\n  Switching to one-sided CI...'
        if  vmode < x_left:
            n3 = int(2 * nm * alpha)
            print vmode, '|', x_left, x_right
            x_right = vs[n3]
            print 'theta < ', x_right
            x_left = None
        else:
            n3 = int(nm * (1. - 2 * alpha))
            print vmode, '|', x_left, x_right
            x_left = vs[n3]
            print 'theta > ', x_left
            x_right = None

    print x_left, x_right
    #   print vmode-2*vstd, vmode+2*vstd
    #   print '--------------------------------'

    return x, y, x_left, x_right


#==========================================================================
def get_y(x0, x, y):
    # find x_i, x_i+1 such that x_i < x0 < x_i+1  -->  y0 = y(x_i)/2 + y(x_i+1)/2
    # or x0 == x_i  --> y0 = y(x0)
    n = len(x)
    if x0 < x[0]:
        return y[0]
    elif x0 > x[n - 1]:
        return y[n - 1]

    for i in range(n):
        if x0 == x[i]:
            return y[i]
        elif x0 > x[i] and x0 < x[i + 1]:
            if x0 - x[i] > x[i + 1] - x0:
                return y[i + 1]
            else:
                return y[i]

    print 'get_y:  a problem!!!'


#==========================================================================
def plot_modelA(values, confidence, dpidpi, numbins, x_best):
    fig1 = pyplot.figure(num=None, dpi=dpidpi, facecolor='w', edgecolor='k')
    rect = [0.1, 0.1, 0.8, 0.8]
    ax1 = fig1.add_axes(rect)

    x_left = zeros(len(x_best), float)
    x_right = zeros(len(x_best), float)
    delta = 0
    leg0 = ['$A_1$', '$A_2$', '$A_3$', '$A_4$', '$A_5$', '$A_6$', '$A_7$',
            '$A_8$']
    pyplot.title(
        'Annotator-specific accuracy ($\\theta_i$ $\\rightarrow$ $A_i$)')

    increment_delta = False

    for i in range(8):
        v_tmp = values[:, i]
        x, y, xl, xr = analyse_parameter_distribution(v_tmp, confidence,
                                                      numbins)
        x_left[i] = xl
        x_right[i] = xr
        col = cm.jet(i / 8.)
        step(x, y + delta, linewidth=3, color=col, linestyle='-', where='mid',
             label=leg0[i])
        ax1.plot([xl, xl], [0 + delta, get_y(xl, x, y) + delta], [xr, xr],
            [0 + delta, get_y(xr, x, y) + delta], color=col, linestyle='-',
                         label='_nolegend_')
        ax1.plot([x_best[i], x_best[i]],
            [0, get_y(x_best[i], x, y) + delta], linewidth=1, color=col,
                                       linestyle='--', label='_nolegend_')
        if increment_delta == True:
            delta += max(y)

    xlabel('$\\theta_i$', {'fontsize': 'large'})
    ylabel('$\it{Frequency}$', {'fontsize': 'large'})
    #pyplot.legend()

    leg = ('$\\alpha_1=\\alpha_2=\\alpha_3$', '$\\alpha_4$',
           '$\\alpha_5=\\alpha_6=\\alpha_7$')
    leg1 = ax1.legend(fancybox=True, loc='best')
    leg1.draw_frame(False)

    if len(x_best) > 8:
        fig2 = pyplot.figure(num=None, dpi=dpidpi, facecolor='w', edgecolor='k')
        ax = fig2.add_axes(rect)

        hold(True)
        delta = 0
        xlabel('$\\alpha_i$', {'fontsize': 'large'})
        ylabel('$\it{Frequency}$', {'fontsize': 'large'})
        title('$\\alpha$-parameters: posterior distributions')

        for i in range(8, 11):
            col = cm.jet((i - 8) / 3.)

            v_tmp = values[:, i]
            x, y, xl, xr = analyse_parameter_distribution(v_tmp, confidence,
                                                          numbins)
            x_left[i] = xl
            x_right[i] = xr
            ax.step(x, y + delta, linewidth=3, color=col, linestyle='-',
                    where='mid', label=leg[i - 8])
            ax.plot([xl, xl], [0 + delta, get_y(xl, x, y) + delta], [xr, xr],
                [0 + delta, get_y(xr, x, y) + delta], color=col, linestyle='-',
                            label='_nolegend_')
            ax.plot([x_best[i], x_best[i]],
                [0, get_y(x_best[i], x, y) + delta], linewidth=1, color=col,
                                          linestyle='--', label='_nolegend_')
            if increment_delta == True:
                delta += max(y)

        leg2 = ax.legend(fancybox=True)
        leg2.draw_frame(False)
        #pyplot.legend(loc='best')

    return x_left, x_right


#--------------------------------------------------------------------------
def put_triplet(dicti, like0, x0, mode):
    dicti[mode + '_f_best'] = like0
    dicti[mode + '_x_best'] = x0
    t_best = strftime("%Y-%m-%d %H:%M:%S")
    dicti[mode + '_update_time'] = t_best
    return 0


#-------------------------------------------------------------------------
def get_triplet(dicti, mode):
    f0 = dicti.get(mode + '_f_best', -inf)
    x0 = dicti.get(mode + '_x_best', None)
    t0 = dicti.get(mode + '_update_time', None)
    return f0, x0, t0


#==========================================================================
def load_save_parameters(filename, modelname, f_best, x_best, report):
    filebest = form_filename(filename, '.history')
    print 'load-save'
    curr = modelname + '_' + str(len(x_best))

    if not os.path.isfile(filebest + '.db'):
        print 'new file'
        f = shelve.open(filebest + '.db')
        for model in ['A_model_8', 'A_model_11', 'Bt_model_12']:
            if model == curr:
                put_triplet(f, f_best, x_best, model)
            else:
                put_triplet(f, -inf, None, model)
        f.close()
        return f_best, x_best, strftime("%Y-%m-%d %H:%M:%S")
    else:
        print 'old file'
        f = shelve.open(filebest + '.db')
        f0, x0, t0 = get_triplet(f, curr)

        print 'Stored values:'
        print f0
        print x0
        print t0

        if f0 > f_best:
            f.close()
            return f0, x0, t0
        else:
            put_triplet(f, f_best, x_best, curr)
            f.close()
            return f_best, x_best, strftime("%Y-%m-%d %H:%M:%S")


#------------------------------------------------------------------------------
#==============================================================================
def save_metadata(filename, originaldata, annotators, codes, n, omegas, report):
    filebest = form_filename(filename, '.history')
    print 'Saving metadata ...'

    if not os.path.isfile(filebest + '.db'):
        print 'Your database file <%s> does not exist!!!' % (filebest + '.db')

    f = shelve.open(filebest)
    f['originaldata'] = originaldata
    f['annotators'] = annotators
    f['codes'] = codes
    f['omegas'] = omegas
    f['n'] = n
    f.close()

    return 0


#===========================
class ABmodelGUI(HasTraits):
    model = Enum('A', 'Bt')
    use_priors = Bool(True)
    estimate_alphas = Bool(True)
    number_of_runs = Range(1, 10000, 1)
    run_computation_now = Button('Run')
    use_omegas = Bool(True)
    input_data = File(None)
    optional_labels = File(None)
    estimate_variances = Bool(True)
    Metropolis_jumps = Range(100, 500000, 1000)
    report = Enum('Essentials', 'Everything', 'Nothing')
    target_reject_rate = Range(1, 99, 30)
    evaluation_jumps = Range(200, 5000, 500)
    recomputing_cycle = Range(50, 1000, 100)
    per_cent_delta = Range(0, 30, 20)
    significance = Enum('95%', '99%', '90%')
    figure_dpi = Range(100, 1200, 100)
    # look_at_raw_data = Button('Show raw data')
    raw_annotations = Array(dtype=int32, shape=(None, None))


    def _run_computation_now_fired(self):
        self.run_estimation(self.model,
                            self.use_priors,
                            self.estimate_alphas,
                            self.number_of_runs,
                            self.use_omegas,
                            self.input_data,
                            self.optional_labels,
                            self.estimate_variances,
                            self.Metropolis_jumps,
                            self.report,
                            self.target_reject_rate,
                            self.evaluation_jumps,
                            self.recomputing_cycle,
                            self.per_cent_delta,
                            self.significance,
                            self.figure_dpi,
                            #self.look_at_raw_data,
                            self.raw_annotations)
        return 1


    def _look_at_raw_data_fired(self):
        data_view = View(
            Group(Item(name='raw_annotations', label='Units of annotation'),
                  show_border=True),
            title='Annotators',
            buttons=[CancelButton],
            x=100, y=100, dock='vertical',
            width=700,
            resizable=True
        )
        mat, dim, values, imap, originaldata, annotators, codes, n = check_data(
            self.input_data, self.optional_labels, self.report)
        self.raw_annotations = array(originaldata[0:80, :])

        self.configure_traits(view=data_view)
        print "What now???"


    #============================================================================
    def run_estimation(self, model,
                       use_priors,
                       estimate_alphas,
                       number_of_runs,
                       use_omegas,
                       input_data,
                       optional_labels,
                       estimate_variances,
                       Metropolis_jumps,
                       report,
                       target_reject_rate,
                       evaluation_jumps,
                       recomputing_cycle,
                       per_cent_delta,
                       significance,
                       figure_dpi,
                       #look_at_raw_data,
                       raw_annotations):
        #------------------ getting parameters and deciding what to do... ----------------------
        if cmp(report, 'Nothing') != 0:
            print ''
            print string_wrap('Estimating ...', 3)
            print 'Model: ' + string_wrap(model, 4)
            print 'Use priors: ' + string_wrap(str(use_priors), 4)
            print 'Estimate alphas: ' + string_wrap(str(estimate_alphas), 4)
            print 'Number of runs: ' + string_wrap(str(number_of_runs), 4)
            print 'Use omegas: ' + string_wrap(str(use_omegas), 4)
            print 'Input file: ' + string_wrap(input_data, 4)
            print 'Optional file with labels for figures '\
            + string_wrap(optional_labels, 4)
            print 'Estimate variances: ' + string_wrap(str(estimate_variances),
                                                       4)
            print 'Metropolis jumps: ' + string_wrap(str(Metropolis_jumps), 4)
            print 'Report: ' + string_wrap(str(report), 4)
            print 'Target rejection rate (%): ' + string_wrap(
                str(target_reject_rate), 4)
            print 'Evaluation jumps: ' + string_wrap(str(evaluation_jumps), 4)
            print 'Recomputing cycle: ' + string_wrap(str(recomputing_cycle), 4)
            print 'Per cent of admissible deviation from target rejection: '\
            + string_wrap(str(per_cent_delta), 4)
            print 'Significance: ' + string_wrap(str(significance), 4)
            print 'Figure resolution (dpi): ' + string_wrap(str(figure_dpi), 4)
            print''

        Delta = per_cent_delta * 0.01
        targetreject = target_reject_rate * 0.01
        if cmp(significance, '90%') == 0:
            Level = 0.9
        elif cmp(significance, '95%') == 0:
            Level = 0.95
        else:
            Level = 0.99

        dpi = int(figure_dpi)

        if cmp(model, 'A') == 0:
            modelnumber = 1
            if cmp(report, 'Nothing') != 0:
                print string_wrap("*****A-model*****", 4)
            modelname = 'A_model'
        else:
            if cmp(report, 'Nothing') != 0:
                print string_wrap("*****Bt-model*****", 4)
            modelname = 'Bt_model'
            modelnumber = 2

        tic = time.time()

        estimatealphas = int(estimate_alphas)
        numberOfRuns = int(number_of_runs)
        useomegas = int(use_omegas)
        usepriors = int(use_priors)
        filename = input_data

        np.random.seed()

        #------ prepare data ---------------------------------------------------------------------------------
        mat, dim, values, imap, originaldata, annotators, codes, n = check_data(
            filename, optional_labels, report)
        data = compute_counts(mat, dim)
        FF = zeros(numberOfRuns, float)
        alphas = []
        gammas = []


        #---------
        # model A
        if modelnumber == 1:
            if estimatealphas == True:
                Res = zeros([numberOfRuns, 11], float)
            else:
                Res = zeros([numberOfRuns, 8], float)
            #---------
            # model Bt
        else:
            Res = zeros([numberOfRuns, dim - 1 + 8], float)
        best_f = -Inf

        fileout = form_filename(filename, modelname + '_' + str(
            numberOfRuns) + '_posteriors.txt')
        ffile = open(fileout, "w")

        if cmp(report, 'Nothing') != 0:
            toc = time.time()
            print_wrap(str(toc - tic) + ' seconds has elapsed')


        #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        for j in range(numberOfRuns):
            if cmp(report, 'Nothing') != 0:
                print_wrap(str(j + 1))

            # optimize parameters by maximizing the log likelihood of the model
            if modelnumber == 1:
                # model A
                model_A = ModelA.create_initial_state(dim)
                model_A.mle(mat)
                if estimate_alphas:
                    alpha = model_A._compute_alpha()
                    x_best = np.r_[model_A.theta, [alpha[0], alpha[3], alpha[-1]]]
                else:
                    x_best = model_A.theta.copy()
                FF[j] = model_A.log_likelihood(mat)
            else:
                # model B
                model_Bt = ModelBt.create_initial_state(dim, mat.shape[0],
                                             use_priors=use_priors,
                                             use_omegas=use_omegas)
                model_Bt.mle(mat)
                x_best = model_Bt._params_to_vector(model_Bt.gamma, model_Bt.theta)
                FF[j] = model_Bt.log_likelihood(mat)

            Res[j, :] = x_best[:]
            toc = time.time()
            if cmp(report, 'Nothing') != 0:
                print_wrap(str((toc - tic) / 60) + ' minutes has elapsed')
                print '     '
                print_wrap(' Log-likelihood = ' + str(FF[j]))
            ffile.write(' Log-likelihood = ' + str(FF[j]) + '\n')

            #------------------------------------
            fs, xs, ts = load_save_parameters(filename, modelname, FF[j], x_best
                                              , report)
            #------------------------------------

            # log run results
            if modelnumber == 1:
                ffile.write(
                    ' Thetas: ' + array_format(Res[j, 0:8], '%4.3f ') + '\n')
                if estimatealphas == 1:
                    ffile.write(' Alphas: ' + array_format(Res[j, 8:11],
                                                           '%4.3f ') + '\n')

                if cmp(report, 'Nothing') != 0:
                    print_wrap(
                        ' Thetas: ' + array_format(Res[j, 0:8], '%4.3f '))
                    if estimatealphas == 1:
                        print_wrap(
                            ' Alphas: ' + array_format(Res[j, 8:11], '%4.3f '))
            else:
                ffile.write(' Gammas: ' + array_format(Res[j, 0:dim - 1],
                                                       '%4.3f ') + '\n')
                ffile.write(
                    ' Thetas: ' + array_format(Res[j, dim - 1:dim - 2 + 9],
                                               '%4.3f ') + '\n')
                if cmp(report, 'Nothing') != 0:
                    print_wrap(
                        ' Gammas: ' + array_format(Res[j, 0:dim - 1], '%4.3f '))
                    print_wrap(
                        ' Thetas: ' + array_format(Res[j, dim - 1:dim - 2 + 9],
                                                   '%4.3f '))

            maxL = -Inf
            thetas = zeros(8, float)
            #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


        #--------------------------------------------------------------------------
        # --------------- save meta-data -------------------------------------------
        if modelnumber==1:
            omegas = model_A.omega
        else:
            omegas = []
        save_metadata(filename, originaldata, annotators, codes, n, omegas,
                      report)
        #--------------------------------------------------------------------------
        #-------------------------
        # define best estimates
        x_best = zeros(len(Res[0, :]), float)
        for i in range(numberOfRuns):
            if maxL < FF[i]:
                maxL = FF[i]
                x0 = Res[i, :]
                x_best[:] = x0[:]
        f_best = maxL
        if cmp(report, 'Nothing') != 0:
            print 'Best:'
            print x0

        # try to read the past best estimates for these data
        # save the best results 
        fs, xs, ts = load_save_parameters(filename, modelname, f_best, x_best,
                                          report)
        x0[:] = xs[:]
        x_best[:] = xs[:]

        if cmp(report, 'Nothing') != 0:
            print ''
            print_wrap('Best Log-likelihood so far: ' + str(fs))
            print_wrap('Best parameters so far:')
            print_wrap(array_format(xs, '%4.3f '))

        #----------- now we do have point estimates, but still need to compute
        #--------------- distributions -- with MCMC
        #-------------------------
        # estimate variances and credible intervals of parameters

        if estimate_variances == True:
            if cmp(report, 'Nothing') != 0:
                print string_wrap('**Preparing to compute credible intervals**',
                                  4)
            # all parameters are probabilities, i.e. between 0 and 1
            x_upper = zeros(len(x0), float) + 1.
            x_lower = zeros(len(x0), float)

            if modelnumber == 1:
                model = model_A
            else:
                model = model_Bt
            if cmp(report, 'Nothing') != 0:
                print string_wrap('**Computing credible intervals**', 4)
            Samples = model.sample_posterior_over_accuracy(
                mat, Metropolis_jumps,
                target_rejection_rate = targetreject,
                rejection_rate_tolerance = Delta,
                step_optimization_nsamples = evaluation_jumps,
                adjust_step_every = recomputing_cycle)

            print "Save samples!!!"
            fi = filename.split('.')
            filearray = fi[0] + modelname + '_' + str(
                numberOfRuns) + '_MCMC.txt'
            sp.save(filearray, Samples)
            print "Saved samples ..."

            if cmp(report, 'Nothing') != 0:
                print Samples

            numbins = 25
            dpidpi = 150
            if modelnumber == 1:
                x_left, x_right = plot_modelA(Samples, Level, dpidpi, numbins,
                                              x0)
                for i in range(len(x_best)):
                    print str(x_best[i]), ', CI : [', str(x_left[i]), ',', str(
                        x_right[i]), ']'
                print ' '
                show()

            # -------- now we can return to annotations and provide them with posterior probabilities:
            # ---------------------------------------------------------------------------------------------
            # ---------------------------------------------------------------------------------------------
            # compute MAP annotations under model A
        maxL = -Inf
        if modelnumber == 1:
            for i in range(numberOfRuns):
                if estimatealphas == True:
                    if cmp(report, 'Nothing') != 0:
                        print "Run #" + str(i + 1) + ": "\
                              + str(FF[i]) + "|" + str(Res[i, 0:8])\
                              + "|" + str(Res[i, 8:])
                else:
                    if cmp(report, 'Nothing') != 0:
                        print "Run #" + str(i + 1)\
                              + ": "\
                              + str(FF[i])\
                              + "|" + str(Res[i, :])

                if maxL < FF[i]:
                    maxL = FF[i]
                    thetas = Res[i, 0:8]

                if estimatealphas == True:
                    alphas[0] = Res[i, 8]
                    alphas[1] = Res[i, 8]
                    alphas[2] = Res[i, 8]
                    alphas[3] = Res[i, 9]
                    alphas[4] = Res[i, 10]
                    alphas[5] = Res[i, 10]
                    alphas[6] = Res[i, 10]
                else:
                    alphas = model_A._compute_alpha()
            post = format_posteriors(mat, model_A._compute_alpha(), dim,
                                     model_A.theta, [], modelnumber,
                                     model_A)
        else:
            # compute posteriors
            post = format_posteriors(mat, alphas, dim, thetas, gammas, modelnumber,
                                     model_Nt)

        post = array(post, float)

        for i in range(post.shape[0]):
            ffile.write(
                array_format(originaldata[i, :], ' %d,') + '|' + array_format(
                    post[i, :], '%5.4f,') + '\n')
            if cmp(report, 'Everything') == 0:
                ind = array(where(originaldata[i, :] > 0), int).flatten()
                s1 = array_format(originaldata[i, :], '%d ')
                s2 = array_format(post[i, :], '%4.3f ')
                s3 = array_format(thetas[ind], '%5.4f ')
                print string_wrap(s1, 1) + "|" + string_wrap(s2,
                                                             2) + "|" + string_wrap(
                    s3, 3)

        if cmp(report, 'Everything') == 0:
            print string_wrap(
                '*Data* | *Posteriors* for all annotation values [1, 2, ...N_max] | *thetas* for the three evaluators'
                , 1)

        ffile.close()


#==========================================================
#              Main
#----------------------------------------------------------
if __name__ == '__main__':
    import sys, os


    main_view = View(Group(Item(name='input_data'),
                           Item(name='optional_labels',
                                label='Optional file with labels for codes'),
                           Item(name='model', style='custom'),
                           Item(name='number_of_runs'),
                           Item(name='use_priors',
                                tooltip='Use informative prior distribution on accuracy parameters')
                           ,
                           Item(name='_'),
                           Item(name='estimate_alphas',
                                label='A: estimate *alphas*',
                                enabled_when="model=='A'",
                                tooltip='Estimate *alphas* with the maximum likelihood method')
                           ,
                           Item(name='use_omegas',
                                label='Bt: use *omegas*',
                                enabled_when="model=='Bt'",
                                tooltip='Use *omegas* to initialize *gammas*'),
                           Item(name='_'),
                           Item(name='estimate_variances',
                                enabled_when="input_data!=None"),
                           Item(name='Metropolis_jumps',
                                label='Number of Metropolis-Hastings jumps',
                                enabled_when="estimate_variances==True"),
                           Item(name='_'),
                           Item(name='report', label='Output verbosity level '),
                           Item(name='_'),
                           Item(name='target_reject_rate', style='custom',
                                format_str='%4.3f',
                                enabled_when="input_data!=None and estimate_variances==True")
                           ,
                           Item(name='evaluation_jumps',
                                enabled_when="input_data!=None and estimate_variances==True")
                           ,
                           Item(name='recomputing_cycle',
                                enabled_when="input_data!=None and estimate_variances==True")
                           ,
                           Item(name='per_cent_delta',
                                label='Maximum deviation from the target rejection rate (%)'
                                ,
                                enabled_when="input_data!=None and estimate_variances==True")
                           ,
                           Item(name='significance',
                                enabled_when="input_data!=None and estimate_variances==True")
                           ,
                           Item(name='figure_dpi',
                                label='Resolution of figures (dpi)',
                                enabled_when="input_data!=None and estimate_variances==True")
                           ,
                           Item(name='_'),
                           Item(name='run_computation_now',
                                enabled_when="input_data!=None",
                                show_label=False),
                           #Item(name='look_at_raw_data',enabled_when="input_data!=None",show_label=False),
                           show_border=True),
                     title='Options:',
                     buttons=[CancelButton],
                     x=100, y=100, dock='vertical',
                     width=700,
                     resizable=True
    )

    data_view = View(Group(Item(name='raw_annotations'),
                           show_border=True),
                     title='Raw annotations:',
                     buttons=[CancelButton],
                     x=100, y=100, dock='vertical',
                     width=700,
                     resizable=True
    )
    gui = ABmodelGUI()
    gui.configure_traits(view=main_view)

    if cmp(gui.report, 'Nothing') != 0:
        print '''    

    *Reference:*

    Rzhetsky A, Shatkay H, Wilbur WJ (2009) 
            How to Get the Most out of Your Curation Effort. 
            PLoS Comput Biol 5(5): e1000391. 
            doi:10.1371/journal.pcbi.1000391
            '''
