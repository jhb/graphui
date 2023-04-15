"""
This is a wrapper around iterables, that allows to access or call attributes
and functions of the members of the iterables. The respective results are
wrapped again in a ForwardList, so that this can go on endless.

The main purpose is for doing graph queries gremlin style.

    >>> texts = ['One','one','Two','Three']
    >>> f = ForwardList(texts)
    >>> sorted(f.title())
    ['One', 'Three', 'Two']

We only got three items, because we try to deduplicate results on every hop.

"""

from typing import Self

class ForwardList(list):

    def __init__(self,obj):
        # deduplicate entries
        out = set()
        for a in obj:
            if type(a) in (ForwardList,tuple,list):
                for b in a:
                    out.add(b)
            else:
                out.add(a)
        super().__init__(out)

    def __getattr__(self,item) -> Self:
        return ForwardList(getattr(i,item,None) for i in self)

    def __getitem__(self,item) -> Self:
        return ForwardList(i.get(item, None) for i in self)

    def __call__(self,*args,**kwargs) -> Self:
        return ForwardList(i(*args,**kwargs) for i in self)

    def __hash__(self):
        return id(self)