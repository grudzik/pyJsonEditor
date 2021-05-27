"""parse token list to recursive JsonNodes"""
from typing import List
import pytest
from token_list import TokenList
class JsonNode:
    """ json node with begin end end children"""
    def __init__(self, obj_type, **kwargs):
        self.type = obj_type
        self.start = kwargs['start']
        self.end = kwargs['end']
        self.name = kwargs.get('name','')
        self.kids = kwargs.get('kids',[])
        if 'value' in kwargs:
            self.kids = [kwargs['value']]

    def append(self,obj):
        """add one child"""
        self.kids.append( obj )

    def __repr__(self):
        return self.to_string()

    def to_string(self,depth=0):
        """this object as string"""
        prefix=' '*(2*depth)
        if self.type=='value':
            return f'JsonNode::{self.type}[{self.start}..{self.end}] = {self.kids[0]}'

        return f'JsonNode::{self.type}[{self.start}..{self.end}] ' +\
               f'\n{prefix}{{\n' +\
               ',\n'.join([ ' '*(2*(depth+1))+
                             str(i)+
                             ( '="'+child.name+'"' if child.name else '' )+
                             ": "+child.to_string(depth+1) for i,child in enumerate(self.kids)]) +\
               f'\n{prefix}}}'

    def __eq__(self, obj):
        return isinstance(obj, JsonNode) and\
                obj.start == self.start and\
                obj.end == self.end and\
                obj.type == self.type and\
                obj.kids == self.kids and\
                obj.name == self.name


def eat_value(tok: TokenList) -> JsonNode:
    """
    convert value tokens to object
    V -> JsonNode
    """
    begin = tok.expect_pop('v', 'not a value')
    ret = JsonNode('value',
                   start=begin[1],
                   end=(begin[1] + len(begin[2])))
    ret.append(begin[2]) #payload as first child
    return ret

def eat_child(tok: TokenList) -> JsonNode:
    """
    (V|A|D)
    """
    ret = None
    if   tok.next_is('v'):
        ret = eat_value(tok)
    elif tok.next_is('['):
        ret = eat_array(tok)
    elif tok.next_is('{'):
        ret = eat_dict(tok)
    return ret

def eat_dict(tok:TokenList) -> JsonNode:
    """
    convert dict tokens to object,
    basicalyy array with named items
    '{' 'S':(V|A|D)* '}'
    """
    begin = tok.expect_pop('{', 'not object')
    ret = JsonNode('dict',
                   start=begin[1],
                   end=False)

    while tok.peek():

        if tok.next_is('S'):

            name = tok.pop()
            if len(name) != 3 or not name[2]:
                tok.raise_token_error('string koken is missing value')
            tok.expect_pop(':', 'not string')
            child = eat_child(tok)
            if not child:
                tok.raise_token_error('missing child')
            child.name = name[2]
            ret.append(child)

            if tok.next_is(','):
                tok.pop()
                continue

        end = tok.expect_pop('}', 'object error, unexpectd token: {}'.format( str(tok.peek()) ))
        ret.end = end[1]
        return ret

    tok.raise_token_error('object not closed')


def eat_array(tok:TokenList) -> JsonNode:
    """
    convert array tokens to object
    '[' ( V|A|D )* ']'
    """
    begin = tok.expect_pop('[', 'not array')

    ret = JsonNode('array',
                   start=begin[1],
                   end=False)
    while tok.peek():

        child = eat_child(tok)
        if child:
            ret.append(child)
            if tok.next_is(','):
                tok.pop()
                continue

        end = tok.expect_pop(']', 'array error unexpectd token: {}'.format( str(tok.peek()) ))
        ret.end = end[1]
        return ret

    tok.raise_token_error('array error, object not closed')

def parse(tokens:List) -> JsonNode:
    """
    Conver tokens into object (dict)
    """
    tok = TokenList(tokens)
    return eat_dict(tok)


############################## TESTS ##############################

def test_json_node_to_string():
    """ JsonNode tests """
    ret = str(JsonNode('dict', start=0,end=19,))
    assert ret == 'JsonNode::dict[0..19] \n{\n\n}'

    ret = JsonNode('value', start=1,end=2)
    ret.kids=['ok']
    assert str(ret) == 'JsonNode::value[1..2] = ok'


testdata = [
(   #'{"a":1}'
    [('{', 0), ('}', 1)],
    JsonNode('dict', start=0, end=1)
)
,
(   #'{"b":1}'
    [('{', 0), ('S', 1, 'b'), (':', 4), ('v', 5, '1'), ('}', 6)],
    JsonNode('dict',
       start=0,
       end=6,
       kids=[
           JsonNode('value', start=5,end=6, name='b', value='1')
       ])
)
,
(   #'{"c":[]}
    [('{', 0), ('S', 1, 'c'), (':', 4), ('[', 5), (']', 6), ('}', 7)],
    JsonNode('dict',
       start=0,
       end=7,
       kids=[
           JsonNode('array', start=5,end=6, name='c')
       ])
)
,
(   #'{"d":{}}
    [('{', 0), ('S', 1, 'd'), (':', 4), ('[', 5), (']', 6), ('}', 7)],
    JsonNode('dict',
       start=0,
       end=7,
       kids=[
           JsonNode('array', start=5,end=6, name='d')
       ])
)
,
(
    #{"e":{"f":1}}
    [('{', 0),
      ('S', 1, 'e'), (':', 4),
         ('{', 5),
             ('S', 6, 'f'), (':', 9), ('v', 10, '1'),
         ('}', 11),
      ('}', 12)],
    JsonNode('dict',
        start=0,
        end=12,
        kids=[
            JsonNode('dict',
             start=5,
             end=11,
             name='e',
             kids=[
                 JsonNode('value',start=10,end=11, name='f', value='1')
             ]
            )
        ]
    )
)
]

@pytest.mark.parametrize("tokens,expected", testdata)
def test_parse(tokens, expected):
    """ throw all expceptions """
    ret = parse(tokens)
    assert ret == expected
