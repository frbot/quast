############################################################################
# Copyright (c) 2011-2015 Saint-Petersburg Academic University
# All Rights Reserved
# See file LICENSE for details.
############################################################################

import logging
import os
import itertools
import fastaparser
from libs.html_saver import json_saver
from libs import qconfig, qutils
from qutils import index_to_str
import reporting

from libs.log import get_logger
logger = get_logger(qconfig.LOGGER_DEFAULT_NAME)


def parallel_get_length_and_GC_content(index, contigs_fpath, skip=False, reference=False):
    """
       Returns percent of GC for assembly and GC distribution: (list of GC%, list of # windows)
    """
    if not reference:
        assembly_label = qutils.label_from_fpath(contigs_fpath)
        logger.info('    ' + qutils.index_to_str(index) + assembly_label)
        #lists_of_lengths.append(fastaparser.get_lengths_from_fastafile(contigs_fpath))
        list_of_length = []
        number_of_Ns = 0
    total_GC_amount = 0
    total_contig_length = 0
    GC_bin_num = int(100 / qconfig.GC_bin_size) + 1
    GC_distribution_x = [i * qconfig.GC_bin_size for i in range(0, GC_bin_num)] # list of X-coordinates, i.e. GC %
    GC_distribution_y = [0] * GC_bin_num # list of Y-coordinates, i.e. # windows with GC % = x
    total_GC = None
    if skip:
        return total_GC, (GC_distribution_x, GC_distribution_y)

    for name, seq_full in fastaparser.read_fasta(contigs_fpath): # in tuples: (name, seq)
        # list_of_length.append(len(seq))
        if not reference:
            number_of_Ns += seq_full.count('N')
            list_of_length.append(len(seq_full))
        if not skip:
            total_GC_amount += seq_full.count("G") + seq_full.count("C")
            total_contig_length += len(seq_full) - seq_full.count("N")
            n = 100 # blocks of length 100
            # non-overlapping windows
            for seq in [seq_full[i:i+n] for i in range(0, len(seq_full), n)]:
                # skip block if it has less than half of ACGT letters (it also helps with "ends of contigs")
                ACGT_len = len(seq) - seq.count("N")
                if ACGT_len < (n / 2):
                    continue

                GC_len = seq.count("G") + seq.count("C")
                GC_percent = 100.0 * GC_len / ACGT_len
                GC_distribution_y[int(int(GC_percent / qconfig.GC_bin_size) * qconfig.GC_bin_size)] += 1

#    GC_info = []
#    for name, seq_full in fastaparser.read_fasta(contigs_fpath): # in tuples: (name, seq)
#        total_GC_amount += seq_full.count("G") + seq_full.count("C")
#        total_contig_length += len(seq_full) - seq_full.count("N")
#        n = 100 # blocks of length 100
#        # non-overlapping windows
#        for seq in [seq_full[i:i+n] for i in range(0, len(seq_full), n)]:
#            # skip block if it has less than half of ACGT letters (it also helps with "ends of contigs")
#            ACGT_len = len(seq) - seq.count("N")
#            if ACGT_len < (n / 2):
#                continue
#            # contig_length = len(seq)
#            GC_amount = seq.count("G") + seq.count("C")
#            #GC_info.append((contig_length, GC_amount * 100.0 / contig_length))
#            GC_info.append((1, 100 * GC_amount / ACGT_len))

#        # sliding windows
#        seq = seq_full[0:n]
#        GC_amount = seq.count("G") + seq.count("C")
#        GC_info.append((1, GC_amount * 100.0 / n))
#        for i in range(len(seq_full) - n):
#            GC_amount = GC_amount - seq_full[i].count("G") - seq_full[i].count("C")
#            GC_amount = GC_amount + seq_full[i + n].count("G") + seq_full[i + n].count("C")
#            GC_info.append((1, GC_amount * 100.0 / n))

    if total_contig_length == 0:
        total_GC = None
    else:
        total_GC = total_GC_amount * 100.0 / total_contig_length
    if not reference:
        return list_of_length, number_of_Ns, total_GC, (GC_distribution_x, GC_distribution_y)
    else:
        return total_GC, (GC_distribution_x, GC_distribution_y)


def do(ref_fpath, contigs_fpaths, output_dirpath, json_output_dir, results_dir):
    logger.print_timestamp()
    logger.info("Running Basic statistics processor...")
    
    if not os.path.isdir(output_dirpath):
        os.mkdir(output_dirpath)

    reference_length = None
    if ref_fpath:
        reference_length = qconfig.ref_len
        if reference_length == 0:
            reference_length = sum(fastaparser.get_lengths_from_fastafile(ref_fpath))
            qconfig.ref_len = reference_length
        reference_GC, reference_GC_distribution = parallel_get_length_and_GC_content(0, ref_fpath, skip=False, reference=True)

        logger.info('  Reference genome:')
        logger.info('    ' + os.path.basename(ref_fpath) + ', Reference length = ' + str(reference_length) + ', Reference GC % = ' + '%.2f' % reference_GC)
    elif qconfig.estimated_reference_size:
        reference_length = qconfig.estimated_reference_size
        qconfig.ref_len = reference_length
        logger.info('  Estimated reference length = ' + str(reference_length))

    if reference_length:
        # Saving the reference in JSON
        if json_output_dir:
            json_saver.save_reference_length(json_output_dir, reference_length)

        # Saving for an HTML report
        if qconfig.html_report:
            from libs.html_saver import html_saver
            html_saver.save_reference_length(results_dir, reference_length)

    logger.info('  Contig files: ')
    n_jobs = min(qconfig.max_threads, len(contigs_fpaths))
    from joblib import Parallel, delayed
    results = Parallel(n_jobs=n_jobs)(delayed(parallel_get_length_and_GC_content)(index, contigs_fpath, qconfig.no_gc, reference=False) for (index, contigs_fpath) in enumerate(contigs_fpaths))
    lists_of_lengths = [result[0] for result in results]
    numbers_of_Ns = [result[1] for result in results]
    total_GCs = [result[2] for result in results]
    GC_distributions = [result[3] for result in results]
    num_contigs = max([len(list_of_length) for list_of_length in lists_of_lengths])

    multiplicator = 1
    if num_contigs > qconfig.max_points:
        import math
        multiplicator = int(math.ceil(int(num_contigs/qconfig.max_points)))
        lists_of_lengths = [sorted(list, reverse=True) for list in lists_of_lengths]
        corr_lists_of_lengths = [[sum(list_of_length[((i-1)*multiplicator):(i*multiplicator)]) for i in range(1, qconfig.max_points) if (i*multiplicator) < len(list_of_length)]
                            for list_of_length in lists_of_lengths]
        for num_list in range(len(corr_lists_of_lengths)):
            list_len = len(lists_of_lengths[num_list])
            last_index = (int(list_len/multiplicator)-1)*multiplicator
            corr_lists_of_lengths[num_list].append(sum(lists_of_lengths[num_list][last_index:]))
    else:
        corr_lists_of_lengths = lists_of_lengths

    # saving lengths to JSON
    if json_output_dir:
        json_saver.save_contigs_lengths(json_output_dir, contigs_fpaths, corr_lists_of_lengths)
        json_saver.save_tick_x(output_dirpath, multiplicator)

    if qconfig.html_report:
        from libs.html_saver import html_saver
        html_saver.save_contigs_lengths(results_dir, contigs_fpaths, corr_lists_of_lengths)
        html_saver.save_tick_x(results_dir, multiplicator)

    ########################################################################

    logger.info('  Calculating N50 and L50...')

    list_of_GC_distributions = []
    largest_contig = 0
    import N50
    for id, (contigs_fpath, lengths_list, number_of_Ns, total_GC, GC_distribution) in \
            enumerate(itertools.izip(contigs_fpaths, lists_of_lengths, numbers_of_Ns, total_GCs, GC_distributions)):
        report = reporting.get(contigs_fpath)
        n50, l50 = N50.N50_and_L50(lengths_list)
        ng50, lg50 = None, None
        if reference_length:
            ng50, lg50 = N50.NG50_and_LG50(lengths_list, reference_length)
        n75, l75 = N50.N50_and_L50(lengths_list, 75)
        ng75, lg75 = None, None
        if reference_length:
            ng75, lg75 = N50.NG50_and_LG50(lengths_list, reference_length, 75)
        total_length = sum(lengths_list)
        list_of_GC_distributions.append(GC_distribution)
        logger.info('    ' + qutils.index_to_str(id) +
                    qutils.label_from_fpath(contigs_fpath) + \
                    ', N50 = ' + str(n50) + \
                    ', L50 = ' + str(l50) + \
                    ', Total length = ' + str(total_length) + \
                    ', GC % = ' + ('%.2f' % total_GC if total_GC is not None else 'undefined') + \
                    ', # N\'s per 100 kbp = ' + ' %.2f' % (float(number_of_Ns) * 100000.0 / float(total_length)) )
        
        report.add_field(reporting.Fields.N50, n50)
        report.add_field(reporting.Fields.L50, l50)
        if reference_length:
            report.add_field(reporting.Fields.NG50, ng50)
            report.add_field(reporting.Fields.LG50, lg50)
        report.add_field(reporting.Fields.N75, n75)
        report.add_field(reporting.Fields.L75, l75)
        if reference_length:
            report.add_field(reporting.Fields.NG75, ng75)
            report.add_field(reporting.Fields.LG75, lg75)
        report.add_field(reporting.Fields.CONTIGS, len(lengths_list))
        report.add_field(reporting.Fields.LARGCONTIG, max(lengths_list))
        largest_contig = max(largest_contig, max(lengths_list))
        report.add_field(reporting.Fields.TOTALLEN, total_length)
        report.add_field(reporting.Fields.GC, ('%.2f' % total_GC if total_GC is not None else None))
        report.add_field(reporting.Fields.UNCALLED, number_of_Ns)
        report.add_field(reporting.Fields.UNCALLED_PERCENT, ('%.2f' % (float(number_of_Ns) * 100000.0 / float(total_length))))
        if ref_fpath:
            report.add_field(reporting.Fields.REFLEN, int(reference_length))
            report.add_field(reporting.Fields.REFGC, '%.2f' % reference_GC)
        elif reference_length:
            report.add_field(reporting.Fields.ESTREFLEN, int(reference_length))

    import math
    qconfig.min_difference = math.ceil((largest_contig/1000)/600)  # divide on height of plot

    if json_output_dir:
        json_saver.save_GC_info(json_output_dir, contigs_fpaths, list_of_GC_distributions)

    if qconfig.html_report:
        from libs.html_saver import html_saver
        html_saver.save_GC_info(results_dir, contigs_fpaths, list_of_GC_distributions)

    if qconfig.draw_plots:
        import plotter
        ########################################################################import plotter
        plotter.cumulative_plot(ref_fpath, contigs_fpaths, lists_of_lengths, output_dirpath + '/cumulative_plot', 'Cumulative length')
    
        ########################################################################
        # Drawing GC content plot...
        list_of_GC_distributions_with_ref = list_of_GC_distributions
        if ref_fpath:
            list_of_GC_distributions_with_ref.append(reference_GC_distribution)
        # Drawing cumulative plot...
        plotter.GC_content_plot(ref_fpath, contigs_fpaths, list_of_GC_distributions_with_ref, output_dirpath + '/GC_content_plot')

        ########################################################################
        # Drawing Nx and NGx plots...
        plotter.Nx_plot(results_dir, num_contigs > qconfig.max_points, contigs_fpaths, lists_of_lengths, output_dirpath + '/Nx_plot', 'Nx', [])
        if reference_length:
            plotter.Nx_plot(results_dir, num_contigs > qconfig.max_points, contigs_fpaths, lists_of_lengths, output_dirpath + '/NGx_plot', 'NGx', [reference_length for i in range(len(contigs_fpaths))])

    logger.info('Done.')
