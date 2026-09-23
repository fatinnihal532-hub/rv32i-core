// rv32i-core: a single-cycle RV32I integer core.
// Base ISA only (no M/A/F/D, no CSRs, no traps). ECALL/EBREAK/FENCE decode
// as no-ops so ordinary compiler output that includes them doesn't stall.
`default_nettype none

module core #(
    parameter IMEM_WORDS = 512,   // 2 KiB -- plenty for these test programs
    parameter DMEM_WORDS = 256,   // 1 KiB
    parameter IMEM_FILE  = "",
    parameter RESET_PC   = 32'h0
) (
    input  wire clk,
    input  wire rst
);
    reg [31:0] pc;

    // ---- Fetch ----------------------------------------------------------
    wire [31:0] instr;
    mem #(.WORDS(IMEM_WORDS), .INIT_FILE(IMEM_FILE)) imem (
        .clk(clk), .addr(pc), .wdata(32'b0), .we(1'b0),
        .size(3'b010), .rdata(instr)
    );

    wire [6:0] opcode = instr[6:0];
    wire [4:0] rd     = instr[11:7];
    wire [2:0] funct3 = instr[14:12];
    wire [4:0] rs1    = instr[19:15];
    wire [4:0] rs2    = instr[24:20];
    wire [6:0] funct7 = instr[31:25];

    // ---- Decode / control -------------------------------------------------
    // verilator lint_off UNUSEDSIGNAL
    // `illegal` is decoded for documentation/future-trap-support purposes
    // (see docs/methodology.md) but this core has no trap logic, so nothing
    // consumes it yet.
    wire reg_write, mem_write, mem_to_reg, alu_src_imm, branch, jump, jalr, lui, auipc, illegal;
    // verilator lint_on UNUSEDSIGNAL
    wire [3:0] alu_op;
    wire [2:0] mem_size;
    control ctrl (
        .opcode(opcode), .funct3(funct3), .funct7(funct7),
        .reg_write(reg_write), .mem_write(mem_write), .mem_to_reg(mem_to_reg),
        .alu_src_imm(alu_src_imm), .branch(branch), .jump(jump), .jalr(jalr),
        .lui(lui), .auipc(auipc), .alu_op(alu_op), .mem_size(mem_size), .illegal(illegal)
    );

    wire [31:0] imm;
    imm_gen immgen (.instr(instr), .imm(imm));

    // ---- Register file & writeback mux ------------------------------------
    wire [31:0] rs1_data, rs2_data, wb_data;
    wire we_reg_final = reg_write & ~rst;
    regfile rf (
        .clk(clk), .we(we_reg_final), .ra1(rs1), .ra2(rs2), .wa(rd),
        .wd(wb_data), .rd1(rs1_data), .rd2(rs2_data)
    );

    // ---- ALU -----------------------------------------------------------------
    // `zero` is left unconnected: branch conditions are decoded from funct3
    // directly below (BLT/BGE/BLTU/BGEU need signed/unsigned magnitude
    // compares a single zero flag can't express, so BEQ/BNE are decoded the
    // same way for one consistent branch datapath rather than a special case).
    wire [31:0] alu_b = alu_src_imm ? imm : rs2_data;
    wire [31:0] alu_result;
    // verilator lint_off UNUSEDSIGNAL
    wire        alu_zero_unused;
    // verilator lint_on UNUSEDSIGNAL
    alu u_alu (.a(rs1_data), .b(alu_b), .alu_op(alu_op), .result(alu_result), .zero(alu_zero_unused));

    // ---- Data memory ---------------------------------------------------------
    wire [31:0] dmem_rdata;
    mem #(.WORDS(DMEM_WORDS)) dmem (
        .clk(clk), .addr(alu_result), .wdata(rs2_data), .we(mem_write & ~rst),
        .size(mem_size), .rdata(dmem_rdata)
    );

    // ---- Branch resolution (funct3-coded compare, independent of ALU op) ---
    reg branch_taken;
    always @(*) begin
        case (funct3)
            3'b000:  branch_taken = branch & (rs1_data == rs2_data);                     // BEQ
            3'b001:  branch_taken = branch & (rs1_data != rs2_data);                     // BNE
            3'b100:  branch_taken = branch & ($signed(rs1_data) <  $signed(rs2_data));   // BLT
            3'b101:  branch_taken = branch & ($signed(rs1_data) >= $signed(rs2_data));   // BGE
            3'b110:  branch_taken = branch & (rs1_data <  rs2_data);                     // BLTU
            3'b111:  branch_taken = branch & (rs1_data >= rs2_data);                     // BGEU
            default: branch_taken = 1'b0;
        endcase
    end

    // ---- PC-relative results (JAL/AUIPC use PC, JALR uses rs1) --------------
    wire [31:0] pc_plus4    = pc + 32'd4;
    wire [31:0] jal_target  = pc + imm;
    wire [31:0] jalr_target = (rs1_data + imm) & ~32'h1;
    wire [31:0] branch_target = pc + imm;

    // ---- Writeback mux -------------------------------------------------------
    assign wb_data = lui        ? imm :
                      auipc      ? (pc + imm) :
                      jump       ? pc_plus4 :
                      mem_to_reg ? dmem_rdata :
                                   alu_result;

    // ---- Next PC ---------------------------------------------------------------
    wire [31:0] next_pc = jump        ? (jalr ? jalr_target : jal_target) :
                           branch_taken ? branch_target :
                                          pc_plus4;

    always @(posedge clk) begin
        if (rst) pc <= RESET_PC;
        else     pc <= next_pc;
    end

`ifndef SYNTHESIS
    // Simulation-only debug taps, read by the testbench via hierarchical refs.
`endif
endmodule
`default_nettype wire
