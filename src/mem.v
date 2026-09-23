// Synchronous-write / combinational-read byte-addressable memory, used for
// both instruction and data memory in this single-address-space core.
// Loaded at simulation time from a hex file with $readmemh.
// SYNTH_BLACKBOX_MEM (set only by scripts/synth.tcl) marks this module a
// blackbox: yosys keeps its ports for hierarchy but does not expand or
// count its internals. At any real size this array would be an SRAM
// macro from a memory compiler, not synthesizable flip-flops, so counting
// it in gate/area stats would be meaningless -- see scripts/synth.tcl.
`ifdef SYNTH_BLACKBOX_MEM
(* blackbox *)
`endif
module mem #(
    parameter WORDS    = 4096,          // 16 KiB
    parameter INIT_FILE = ""
) (
    input  wire        clk,
    input  wire [31:0] addr,
    input  wire [31:0] wdata,
    input  wire        we,
    input  wire [2:0]  size,      // {unsigned, 00=byte,01=half,10=word}
    output reg  [31:0] rdata
);
    reg [7:0] bytes [0:WORDS*4-1];
    integer i;

    initial begin
        for (i = 0; i < WORDS*4; i = i + 1) bytes[i] = 8'd0;
        if (INIT_FILE != "") $readmemh(INIT_FILE, bytes);
    end

    // Byte reads are staged through plain registers first: a case statement
    // whose branches mix a ternary with a multi-signal concatenation made
    // Icarus Verilog's elaborator hang even on a small array, so the four
    // bytes are fetched once and the sign/zero extension is a plain if/else.
    reg [7:0] b0, b1, b2, b3;
    always @(*) begin
        b0 = bytes[addr];
        b1 = bytes[addr + 1];
        b2 = bytes[addr + 2];
        b3 = bytes[addr + 3];
        if (size[1:0] == 2'b00) begin
            if (size[2]) rdata = {24'b0, b0};
            else         rdata = {{24{b0[7]}}, b0};
        end else if (size[1:0] == 2'b01) begin
            if (size[2]) rdata = {16'b0, b1, b0};
            else         rdata = {{16{b1[7]}}, b1, b0};
        end else begin
            rdata = {b3, b2, b1, b0};
        end
    end

    always @(posedge clk) begin
        if (we) begin
            case (size[1:0])
                2'b00: bytes[addr] <= wdata[7:0];
                2'b01: begin
                    bytes[addr]   <= wdata[7:0];
                    bytes[addr+1] <= wdata[15:8];
                end
                default: begin
                    bytes[addr]   <= wdata[7:0];
                    bytes[addr+1] <= wdata[15:8];
                    bytes[addr+2] <= wdata[23:16];
                    bytes[addr+3] <= wdata[31:24];
                end
            endcase
        end
    end
endmodule
