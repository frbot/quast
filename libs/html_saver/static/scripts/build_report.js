
function showPlotWithInfo(info) {
    var newSeries = [];
    var newColors = [];

    $('#legend-placeholder').find('input:checked').each(function() {
        var number = $(this).attr('name');
        if (number && info.series && info.series.length > 0) {
            var i = 0;
            do {
                var series = info.series[i];
                i++;
            } while (series.number != number && i <= info.series.length);
            //
            if (i <= info.series.length) {
                newSeries.push(series);
                newColors.push(series.color);
            } else {
                console.log('no series with number ' + number);
            }
        }
    });

    if (newSeries.length === 0) {
        newSeries.push({
            data: [],
        });
        newColors.push('#FFF');
    }

    info.showWithData(newSeries, newColors);
}


function buildReport() {
    var assembliesNames;
    var order;

    var totalReport = null;
    var qualities = null;
    var mainMetrics = null;
    var contigsLens = null;
    var coordNx = null;
    var contigsLensNx = null;
    var alignedContigsLens = null;
    var refLen = 0;
    var contigs = null;
    var genesInContigs = null;
    var operonsInContigs = null;
    var gcInfos = null;

    var glossary = JSON.parse($('#glossary-json').html());

    var plotsSwitchesDiv = document.getElementById('plots-switches');
    var plotPlaceholder = document.getElementById('plot-placeholder');
    var legendPlaceholder = document.getElementById('legend-placeholder');
    var scalePlaceholder = document.getElementById('scale-placeholder');

    function getToggleFunction(name, title, drawPlot, data, refPlotValue, tickX) {
        return function() {
            this.parentNode.getElementsByClassName('selected-switch')[0].className = 'plot-switch dotted-link';
            this.className = 'plot-switch selected-switch';
            togglePlots(name, title, drawPlot, data, refPlotValue, tickX)
        };
    }

    var toRemoveRefLabel = true;
    function togglePlots(name, title, drawPlot, data, refPlotValue, tickX) {
        if (name === 'cumulative') {
            $(plotPlaceholder).addClass('cumulative-plot-placeholder');
        } else {
            $(plotPlaceholder).removeClass('cumulative-plot-placeholder');
        }

        var el = $('#reference-label');
        el.remove();

        if (refPlotValue) {
            $('#legend-placeholder').append(
                '<div id="reference-label">' +
                    '<label for="label_' + assembliesNames.length + '_id" style="color: #000000;">' +
                    '<input type="checkbox" name="' + assembliesNames.length +
                    '" checked="checked" id="label_' + assembliesNames.length +
                    '_id">&nbsp;' + 'reference,&nbsp;' +
                    toPrettyString(refPlotValue) +
                    '</label>' +
                    '</div>'
            );
        }

        drawPlot(name, title, colors, assembliesNames, data, refPlotValue, tickX,
            plotPlaceholder, legendPlaceholder, glossary, order, scalePlaceholder);
    }

    var firstPlot = true;
    function makePlot(name, title, drawPlot, data, refPlotValue, tickX) {
        var switchSpan = document.createElement('span');
        switchSpan.id = name + '-switch';
        switchSpan.innerHTML = title;
        plotsSwitchesDiv.appendChild(switchSpan);

        if (firstPlot) {
            switchSpan.className = 'plot-switch selected-switch';
            togglePlots(name, title, drawPlot, data, refPlotValue, tickX);
            firstPlot = false;

        } else {
            switchSpan.className = 'plot-switch dotted-link';
        }

        $(switchSpan).click(getToggleFunction(name, title, drawPlot, data, refPlotValue, tickX));
    }

    /****************/
    /* Total report */

    if (!(totalReport = readJson('total-report'))) {
        console.log("Error: cannot read #total-report-json");
        return 1;
    }

    assembliesNames = totalReport.assembliesNames;

    order = recoverOrderFromCookies() || totalReport.order || Range(0, assembliesNames.length);

    buildTotalReport(assembliesNames, totalReport.report, order, totalReport.date,
        totalReport.minContig, glossary, qualities, mainMetrics);

    if (refLen = readJson('reference-length'))
        refLen = refLen.reflen;

    /****************/
    /* Plots        */

    while (assembliesNames.length > colors.length) {  // colors is defined in utils.js
        colors = colors.concat(colors);
    }

    $(plotsSwitchesDiv).html('<b>Plots:</b>');

    assembliesNames.forEach(function(filename, i) {
        var id = 'label_' + i + '_id';
        $('#legend-placeholder').append('<div>' +
            '<label for="' + id + '" style="color: ' + colors[i] + '">' +
            '<input type="checkbox" name="' + i + '" checked="checked" id="' + id + '">&nbsp;' + filename + '</label>' +
            '</div>');
    });

    var tickX = 1;
    if (tickX = readJson('tick-x'))
        tickX = tickX.tickX;

    if (contigsLens = readJson('contigs-lengths')) {
        makePlot('cumulative', 'Cumulative length', cumulative.draw, contigsLens.lists_of_lengths, refLen, tickX);
    }

    if (coordNx = readJson('coord-nx')) {
        makePlot('nx', 'Nx', nx.draw, {
                coord_x: coordNx.coord_x,
                coord_y: coordNx.coord_y,
            },
            null, null
        );
    }

    if (coordNx = readJson('coord-nax')) {
        makePlot('nax', 'NAx', nx.draw, {
                coord_x: coordNx.coord_x,
                coord_y: coordNx.coord_y,
            },
            null, null
        );
    }

    if (coordNx = readJson('coord-ngx')) {
        makePlot('ngx', 'NGx', nx.draw, {
                coord_x: coordNx.coord_x,
                coord_y: coordNx.coord_y,
            },
            null, null
        );
    }

    if (coordNx = readJson('coord-ngax')) {
        makePlot('ngax', 'NGAx', nx.draw, {
                coord_x: coordNx.coord_x,
                coord_y: coordNx.coord_y,
            },
            null, null
        );
    }


    genesInContigs = readJson('genes-in-contigs');
    operonsInContigs = readJson('operons-in-contigs');
//    if (genesInContigs || operonsInContigs)
//        contigs = readJson('contigs');

    if (genesInContigs) {
        makePlot('genes', 'Genes', gns.draw,  {
                filesFeatureInContigs: genesInContigs.genes_in_contigs,
                kind: 'gene',
            },
            genesInContigs.ref_genes_number, tickX
        );
    }
    if (operonsInContigs) {
        makePlot('operons', 'Operons', gns.draw, {
                filesFeatureInContigs: operonsInContigs.operons_in_contigs,
                kind: 'operon',
            },
            operonsInContigs.ref_operons_number, tickX
        );
    }

    if (gcInfos = readJson('gc')) {
        makePlot('gc', 'GC content', gc.draw, gcInfos, null);
    }

    return 0;
}

