from __future__ import absolute_import
from __future__ import print_function
import sys
import os
import tempfile

import pyverilog
from pyverilog.dataflow.dataflow_analyzer import VerilogDataflowAnalyzer
from pyverilog.dataflow.optimizer import VerilogDataflowOptimizer
from pyverilog.dataflow.graphgen import VerilogGraphGenerator
from pyverilog.vparser.parser import parse
from pyverilog.dataflow.dataflow_analyzer import VerilogDataflowAnalyzer
from pyverilog.ast_code_generator.codegen import ASTCodeGenerator

def analyze_binds(code, topmodule='top'):
    """分析代码中的绑定及其所在的代码块"""
    # 将代码写入临时文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.v', delete=False) as f:
        f.write(code)
        temp_file = f.name
    
    try:
        # 创建数据流分析器
        analyzer = VerilogDataflowAnalyzer([temp_file], topmodule)
        
        # 生成数据流图
        analyzer.generate()
        
        # 获取绑定字典
        binddict = analyzer.getBinddict()
        
        # 创建一个简单的列表来存储所有绑定信息
        binding_info = []
        
        # 收集绑定信息
        for target, bind_list in binddict.items():
            for bind in bind_list:
                # 确定绑定类型
                if bind.alwaysinfo:
                    bind_type = "combination" if bind.alwaysinfo.isCombination() else "clockedge"
                else:
                    bind_type = "assign"
                
                # 创建绑定信息
                bind_info = {
                    'type': bind_type,
                    'lineno': bind.lineno,
                    'dest': str(bind.dest),  # 转换为字符串以避免重复打印
                    'parameterinfo': bind.parameterinfo,

                }
                
                binding_info.append(bind_info)
        
        # 打印函数
        def print_binding_info():
            print("\n=== Bindings and their properties ===")
            for bind in binding_info:
                print("Bind properties:")
                print(f"- Type: {bind['type']}")
                print(f"- lineno: {bind['lineno']}")
                print(f"- dest: {bind['dest']}")
                print(f"- parameterinfo: {bind['parameterinfo']}")
        print_binding_info()
        # 返回收集到的信息
        return binding_info

    finally:
        # 清理临时文件
        os.unlink(temp_file)

# 测试代码
if __name__ == '__main__':
    # 示例Verilog代码
    code = """
module top(
    input clk,
    input rst,
    input [7:0] data_in,
    output c,
    output reg [7:0] data_out
);

reg [7:0] temp;
parameter PARAM1 = 8'd10;

assign c = data_out[7];
always @(posedge clk) begin
    if(rst) begin
        data_out <= 8'b0;
        temp <= 8'b0;
    end else begin
        temp <= data_in;
        data_out <= temp + PARAM1;
    end
end

endmodule
"""
    
    analyze_binds(code)