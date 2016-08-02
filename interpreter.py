import re

class Interpreter:
    
    @staticmethod
    def tokenize(expression):
        if expression == "":
            return []

        regex = re.compile(
            "\s*(=>|[-+*\/\%=\(\)\^<>]|[^-+*\/\%=\(\)\^<>\s]*)\s*")
        tokens = regex.findall(expression)
        return [s for s in reversed(tokens) if s and not s.isspace()]
    
    @staticmethod    
    def check_identifier(token):
        regex = re.compile("^([A-Za-z_])\w*$")
        if not regex.match(token):
            raise ValueError("Invalid Identifier: {0}".format(token))
    
    def __init__(self):
        self.variables = {0: None}
        self.functions = {}
            
    def input(self, expression):
        tokens = Interpreter.tokenize(expression)
        if not expression:
            return ''
        elif tokens[-1] == 'fn':
            tokens.pop()
            return self.define_function(tokens)
        else:
            result = Tree('identity').expand(
                tokens, self.functions).evaluate(self.variables)
            if tokens:
                raise ValueError("Invalid Input: {0}".format(expression))
            return result
            
    def define_function(self, expression):
        name = expression.pop()
        if name in self.variables or name in Tree.ops or name in Tree.keywords:
            raise ValueError(
                "Invalid function name: {0}".format(name))
        f = Function()
        self.functions[name] = f
        try:
            f.set_parameters(expression)
            f.body.expand(expression, self.functions)
        except:
            f.pop(name)
            raise
        return ''
        
class Tree:

    ops = {
        'identity': (0, (lambda l, r, v: r.evaluate(v)), 'right'),
        '=': (1, (lambda l, r, v: l.set_var(r.evaluate(v), v)),   'right'),
        'not': (2, (lambda l, r, v: not r.evaluate(v)), 'right'),
        'is': (2, (lambda l, r, v: l.evaluate(v) == r.evaluate(v)), 'right'),
        '<': (2, (lambda l, r, v: l.evaluate(v) < r.evaluate(v)), 'right'),
        '>': (2, (lambda l, r, v: l.evaluate(v) > r.evaluate(v)), 'right'),
        '+': (3, (lambda l, r, v: l.evaluate(v) + r.evaluate(v)), 'left'),
        '-': (3, (lambda l, r, v: l.evaluate(v) - r.evaluate(v)), 'left'), 
        '/': (4, (lambda l, r, v: l.evaluate(v) / r.evaluate(v)), 'left'),
        '*': (4, (lambda l, r, v: l.evaluate(v) * r.evaluate(v)), 'left'),
        '%': (4, (lambda l, r, v: l.evaluate(v) % r.evaluate(v)), 'left'),
        '^': (5, (lambda l, r, v: l.evaluate(v) ** r.evaluate(v)), 'right'),
        'unary-': (6, lambda l, r, v: -r.evaluate(v), 'right')
        }
        
    keywords = ["fn", "if", "not", "end", "begin"]
        
    def __init__(self, operation):
        ref = Tree.ops[operation]
        self.precedence = ref[0]
        self.procedure = ref[1]
        self.associativity = ref[2]
        self.parent = None
        self.left = None
        self.right = None
        
    def expand(self, expression, functions):
        if not expression:
            return self.origin()
        token = expression.pop()
        if token == 'fn':
            raise ValueError("Function definition within expression")
        elif token in Tree.ops:
            token = self.clarify_operator(token)
            return self.place_node(Tree(token)).expand(
                expression, functions)    
        elif token == ')':
            return self.origin()
        elif self.right:
            expression.append(token)
            return self.origin()
        elif token == 'if':
            self.right = If_clause(expression, functions)
        elif token == 'begin':
            self.right = Sequence(expression, functions)
        elif token == '(':
            self.right = Tree('identity').expand(
                expression, functions)
        elif token in functions:
             self.right = self.application(token, expression, functions)
        else:
             self.right = Symbol(token)
        return self.expand(expression, functions)
             
    def application(self, name, expression, functions):
        arguments = {}
        function_call = functions[name]
        for parameter in function_call.parameters:
            arguments[parameter] = Tree('identity').expand(
            expression, functions)
        return Application(function_call.body, arguments)

    def place_node(self, node):
        if (self.precedence < node.precedence or
                (self.precedence == node.precedence and 
                self.associativity == 'right')):
            self.insert_right(node)
            return self.right
        else:
            return self.parent.place_node(node)
    
    def insert_right(self, obj):
        obj.left = (self.right)
        obj.parent = self
        self.right = obj
    
    def origin(self):
        if self.precedence == 0:
            return self
        else:
            return self.parent.origin()
    
    def clarify_operator(self, operator):
        if operator == '-' and not self.right:
            return 'unary-'
        else:
            return operator
            
    def evaluate(self, variables):
        return self.procedure(self.left, self.right, variables)

class Symbol:
  
    def __init__(self, token):
        self.token = token
        
    def set_var(self, value, variables):
        Interpreter.check_identifier(self.token)
        variables[self.token] = value
        return value
    
    def evaluate(self, variables):
        if not variables:
            try:
                return float(self.token)
            except:
                raise ValueError("Unbound Variable: {0}".format(self.token))
        elif self.token in variables:
            return variables[self.token]
        else:
            return self.evaluate(variables[0])
            
class Function:
    
    def __init__(self):
        self.parameters= []
        self.body = Tree('identity')
        
    def set_parameters(self, expression):
        token = expression.pop()
        if token == '=>':
            return
        Interpreter.check_identifier(token)
        self.parameters.append(token)
        self.set_parameters(expression)

class Application:
    
    def __init__(self, body, args):
        self.arguments = args
        self.body = body
        
    def evaluate(self, variables):
        local_variables = {0: variables}
        for arg, analysis in self.arguments.iteritems():
            local_variables[arg] = analysis.evaluate(variables)
        return self.body.evaluate(local_variables)

class If_clause:

    def __init__(self, expression, functions):
        self.condition = Tree('identity').expand(expression, functions)
        self.true_op = Tree('identity').expand(expression, functions)
        self.false_op = Tree('identity').expand(expression, functions)
        
    def evaluate(self, variables):
        if self.condition.evaluate(variables):
            return self.true_op.evaluate(variables)
        else:
            return self.false_op.evaluate(variables)
            
class Sequence:

    def __init__(self, expression, functions):
        if not expression:
           raise ValueError("Empty sequence")
        self.left = Tree('identity').expand(expression, functions)
        if not expression:
            self.right = None
        else:
            self.right = Sequence(expression, functions)
        
    def evaluate(self, variables):
        if self.right:
            self.left.evaluate(variables)
            return self.right.evaluate(variables)
        else:
            return self.left.evaluate(variables)    
        

