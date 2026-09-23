// Template testbench, filled in by tests/run_case.py with a program's hex
// path and a cycle budget, then compiled and run once per test case.
// On completion it prints x1..x31, then the first 16 data-memory words, in a
// simple line-oriented format the Python harness parses.
`timescale 1ns/1ps
module core_tb;
    reg clk = 0;
    reg rst = 1;

    core #(
        .IMEM_FILE("__IMEM_FILE__")
    ) dut (
        .clk(clk),
        .rst(rst)
    );

    always #5 clk = ~clk;

    integer i;
    initial begin
        rst = 1;
        repeat (2) @(posedge clk);
        rst = 0;
        repeat (__MAX_CYCLES__) @(posedge clk);

        for (i = 1; i <= 31; i = i + 1)
            $display("REG %08x", dut.rf.regs[i]);
        for (i = 0; i < 16; i = i + 1)
            $display("MEM %08x", {dut.dmem.bytes[i*4+3], dut.dmem.bytes[i*4+2],
                                   dut.dmem.bytes[i*4+1], dut.dmem.bytes[i*4]});
        $display("DONE");
        $finish;
    end
endmodule
