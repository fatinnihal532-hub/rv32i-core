// 32 x 32-bit register file. x0 is hardwired to zero (RISC-V convention).
// Two async read ports, one synchronous write port. No same-cycle
// write-to-read forwarding: in a single-cycle core the ALU for the
// instruction being decoded this cycle must see the register file's value
// from *before* this instruction's own write takes effect (the write is
// this instruction's result, not an input to it), so plain async reads
// off the stored array are exactly right -- and forwarding wd back into
// rd1/rd2 would create a real combinational loop whenever rd == rs1/rs2
// (e.g. "addi t0, t0, -1"), since wd is itself derived from rd1/rd2.
module regfile (
    input  wire        clk,
    input  wire        we,
    input  wire [4:0]  ra1,
    input  wire [4:0]  ra2,
    input  wire [4:0]  wa,
    input  wire [31:0] wd,
    output wire [31:0] rd1,
    output wire [31:0] rd2
);
    reg [31:0] regs [1:31];
    integer i;

    initial begin
        for (i = 1; i <= 31; i = i + 1) regs[i] = 32'd0;
    end

    always @(posedge clk) begin
        if (we && wa != 5'd0) regs[wa] <= wd;
    end

    assign rd1 = (ra1 == 5'd0) ? 32'd0 : regs[ra1];
    assign rd2 = (ra2 == 5'd0) ? 32'd0 : regs[ra2];
endmodule
