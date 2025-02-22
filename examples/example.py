from __future__ import absolute_import
from __future__ import print_function
import sys
import os

import pyverilog
from pyverilog.dataflow.dataflow_analyzer import VerilogDataflowAnalyzer
from pyverilog.dataflow.optimizer import VerilogDataflowOptimizer
from pyverilog.dataflow.graphgen import VerilogGraphGenerator
from pyverilog.vparser.parser import parse
from pyverilog.ast_code_generator.codegen import ASTCodeGenerator

def find_node_by_line(nodes, line_number):
    """根据行号查找对应的节点"""
    for node in nodes:
        start_line = node.lineno
        end_line = node.end_lineno if hasattr(node, 'end_lineno') and node.end_lineno else node.lineno
        
        if start_line <= line_number <= end_line:
            return node
    return None

def read_code(sourceFilePath):
    with open(sourceFilePath, 'r') as file:
        code = file.read()
    return code

def analyze_ast(sourceFilePath):
    code = read_code(sourceFilePath)
    ast, directives = parse([code])
    
    # 创建代码生成器
    codegen = ASTCodeGenerator()
    
    # 存储不同类型的节点
    nodes = {
        'ModuleDef': [],
        'Paramlist': [],
        'Portlist': [],
        'Decl': [],
        'Always': [],
        'Assign': [],
        'Function': [],
        'Task': [],
        'Initial': [],
    }
    
    # 遍历AST收集节点
    def visit(node):
        if node.__class__.__name__ in nodes:
            nodes[node.__class__.__name__].append(node)
        for c in node.children():
            visit(c)
    
    visit(ast)
    
    # 将所有节点放入一个列表
    all_nodes = []
    for node_list in nodes.values():
        all_nodes.extend(node_list)
    
    # 按行号排序
    sorted_nodes = sorted(all_nodes, key=lambda x: x.lineno)
    
    # 移除嵌套的行号范围
    def remove_nested_ranges(nodes):
        result = []
        current_end = 0
        
        for node in nodes:
            if node.lineno > current_end:
                result.append(node)
                if hasattr(node, 'end_lineno') and node.end_lineno:
                    current_end = node.end_lineno
                else:
                    current_end = node.lineno
        
        return result
    
    # 移除嵌套的节点
    non_nested_nodes = remove_nested_ranges(sorted_nodes)

    return non_nested_nodes

def analyze_dfg(sourceFilePath, non_nested_nodes, topmodule):
    analyzer = VerilogDataflowAnalyzer(sourceFilePath, topmodule,
                                       noreorder=False,
                                       nobind=False,
                                       preprocess_include=[],
                                       preprocess_define=[])
    analyzer.generate()

    directives = analyzer.get_directives()
    terms = analyzer.getTerms()
    binddict = analyzer.getBinddict()

    optimizer = VerilogDataflowOptimizer(terms, binddict)

    optimizer.resolveConstant()
    resolved_terms = optimizer.getResolvedTerms()
    resolved_binddict = optimizer.getResolvedBinddict()
    constlist = optimizer.getConstlist()

    graphgen = VerilogGraphGenerator(topmodule, terms, binddict,
                                     resolved_terms, resolved_binddict, constlist, 'out.png')

    codegen = ASTCodeGenerator()
    binding_info = []
    for name, bindlist in binddict.items():
        for bind in bindlist:
            graphgen.generate(str(bind.dest), walk=False, identical=False,
                        step=1, do_reorder=False, delay=False, alwaysinfo=bind.alwaysinfo, withcolor=True)
            if bind.alwaysinfo:
                    bind_type = "combination" if bind.alwaysinfo.isCombination() else "clockedge"
            else:
                bind_type = "assign"
                
            node = find_node_by_line(non_nested_nodes, bind.lineno)
            if node:
                range = (f"{node.lineno}-{node.end_lineno if hasattr(node, 'end_lineno') and node.end_lineno else node.lineno}")
                code = (codegen.visit(node))

            bind_info = {
                'type': bind_type,
                'range': range,
                'dest': str(bind.dest),  # 转换为字符串以避免重复打印
                'parameterinfo': bind.parameterinfo,
                'code': code,
            }
                
            binding_info.append(bind_info)


    def print_binding_info():
            print("\n=== Bindings and their properties ===")
            for bind in binding_info:
                print("Bind properties:")
                print(f"- Type: {bind['type']}")
                print(f"- dest: {bind['dest']}")
                print(f"- parameterinfo: {bind['parameterinfo']}")

    return (graphgen.graph.to_string()), binding_info

def code_analyze(sourceFilePath):
    non_nested_nodes = analyze_ast(sourceFilePath=sourceFilePath)
    dfg = []
    bind = []
    for node in non_nested_nodes:
        if node.__class__.__name__ == 'ModuleDef':
            dfg_single, bind_single = analyze_dfg(sourceFilePath=sourceFilePath,non_nested_nodes=non_nested_nodes, topmodule=node.name)
            dfg.append(dfg_single)
            bind.append(bind_single)
    head = [node for node in non_nested_nodes 
                       if node.__class__.__name__ in ['ModuleDef', 'Paramlist', 'Portlist', 'Decl']]

    return head, bind, dfg
