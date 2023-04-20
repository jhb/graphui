function nodedetails (nodeid){
    htmx.ajax('GET','/node/'+nodeid,'#detail');
}

function edgedetails (edgeid){
    htmx.ajax('GET','/edge/'+edgeid,'#detail');
}