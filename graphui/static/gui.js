function nodedetails (nodeid){
    htmx.ajax('GET','/node/'+nodeid,'#detail');
}