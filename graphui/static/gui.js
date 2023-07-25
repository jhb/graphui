function nodedetails(nodeid) {
    htmx.ajax('GET', '/node/' + nodeid, '#detail');
}

function edgedetails(edgeid) {
    htmx.ajax('GET', '/edge/' + edgeid, '#detail');
}

var nodeinfo_hide = true;

function hx_nodeinfo(nodeid) {
    htmx.ajax('GET', 'nodeinfo', {target: '#nodeinfo', swap: 'innerHTML', values: {nodeid: nodeid}})
}

function nodeinfo_show(e) {
    nodeinfo_hide = false;
    var info_element = $(e.currentTarget).closest(".nodeinfo")[0];
    hx_nodeinfo($(info_element).data('nodeid'));
    var nodeinfo = $('#nodeinfo');
    var infowidth = nodeinfo.css('width');
    infowidth = infowidth.substring(0, infowidth.length - 2);
    var x = e.pageX < ($(window).width() - infowidth) ? e.pageX : e.pageX - infowidth - 50;
    nodeinfo
        .show()
        .css('left', x)
        .css('top', e.pageY - 70)
}

function nodeinfo_leave() {
    nodeinfo_hide = true;
    timeout = 500;
    setTimeout(() => {
        if (nodeinfo_hide) {
            $('#nodeinfo').hide();
        }
    }, timeout);
}

function addSelection(e) {
    let choice = $(e.currentTarget).closest('.choice');
    let nodeid = choice.data('nodeid');
    let value = choice.find('.nodename').first().html();
    let rendered = $('#template').first().html().replaceAll('$value$', value).replaceAll('$nodeid$', nodeid);
    $(rendered).insertBefore('.chevron');
    $('.comboinput').focus();
    $('.nodeinfo').off('.nodeinfo').on('mouseover.nodeinfo', nodeinfo_show).on('mouseleave.nodeinfo', nodeinfo_leave);
    $('.remove').on('click.nodeinfo', (e) => {
        nodeinfo_leave();
        $(e.target).closest('.comboelement').remove();
        return false
    })
}