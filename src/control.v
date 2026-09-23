// Main + ALU control. Decodes opcode/funct3/funct7 into the datapath's
// control signals. Combinational only -- the core is single-cycle.
module control (
    input  wire [6:0] opcode,
    input  wire [2:0] funct3,
    input  wire [6:0] funct7,
    output reg        reg_write,
    output reg        mem_write,
    output reg        mem_to_reg,   // 1: writeback = memory read data
    output reg        alu_src_imm,  // 1: ALU operand B = immediate
    output reg        branch,
    output reg        jump,         // JAL / JALR (unconditional)
    output reg        jalr,         // 1: target base is rs1, not PC
    output reg        lui,
    output reg        auipc,
    output reg  [3:0] alu_op,
    output reg  [2:0] mem_size,     // {unsigned, size[1:0]}: 00 byte,01 half,10 word
    output reg        illegal
);
    localparam OP_LOAD   = 7'b0000011;
    localparam OP_STORE  = 7'b0100011;
    localparam OP_BRANCH = 7'b1100011;
    localparam OP_JAL    = 7'b1101111;
    localparam OP_JALR   = 7'b1100111;
    localparam OP_LUI    = 7'b0110111;
    localparam OP_AUIPC  = 7'b0010111;
    localparam OP_IMM    = 7'b0010011;
    localparam OP_REG    = 7'b0110011;
    localparam OP_SYSTEM = 7'b1110011; // ECALL/EBREAK/FENCE: decoded, treated as NOP

    localparam ALU_ADD  = 4'h0, ALU_SUB = 4'h1, ALU_AND = 4'h2, ALU_OR = 4'h3,
               ALU_XOR  = 4'h4, ALU_SLL = 4'h5, ALU_SRL = 4'h6, ALU_SRA = 4'h7,
               ALU_SLT  = 4'h8, ALU_SLTU = 4'h9;

    // verilator lint_off UNUSEDSIGNAL
    // Only f7[5] is architecturally meaningful here (it's what distinguishes
    // ADD/SUB and SRL/SRA); the rest of funct7 is reserved-as-zero for these
    // opcodes in RV32I, so the other 6 bits are legitimately unused.
    function [3:0] alu_op_reg_imm;
        input [2:0] f3;
        input [6:0] f7;
        input       is_imm_shift; // SRLI/SRAI share funct3 with SRL/SRA
        begin
            case (f3)
                3'b000: alu_op_reg_imm = (f7[5] && !is_imm_shift) ? ALU_SUB : ALU_ADD; // ADD/SUB, ADDI
                3'b001: alu_op_reg_imm = ALU_SLL;
                3'b010: alu_op_reg_imm = ALU_SLT;
                3'b011: alu_op_reg_imm = ALU_SLTU;
                3'b100: alu_op_reg_imm = ALU_XOR;
                3'b101: alu_op_reg_imm = f7[5] ? ALU_SRA : ALU_SRL;
                3'b110: alu_op_reg_imm = ALU_OR;
                3'b111: alu_op_reg_imm = ALU_AND;
                default: alu_op_reg_imm = ALU_ADD;
            endcase
        end
    endfunction
    // verilator lint_on UNUSEDSIGNAL

    always @(*) begin
        reg_write   = 1'b0;
        mem_write   = 1'b0;
        mem_to_reg  = 1'b0;
        alu_src_imm = 1'b0;
        branch      = 1'b0;
        jump        = 1'b0;
        jalr        = 1'b0;
        lui         = 1'b0;
        auipc       = 1'b0;
        alu_op      = ALU_ADD;
        mem_size    = funct3;
        illegal     = 1'b0;

        case (opcode)
            OP_REG: begin
                reg_write = 1'b1;
                alu_op    = alu_op_reg_imm(funct3, funct7, 1'b0);
            end
            OP_IMM: begin
                reg_write   = 1'b1;
                alu_src_imm = 1'b1;
                alu_op      = alu_op_reg_imm(funct3, funct7, 1'b1);
            end
            OP_LOAD: begin
                reg_write   = 1'b1;
                alu_src_imm = 1'b1;
                mem_to_reg  = 1'b1;
                alu_op      = ALU_ADD;
            end
            OP_STORE: begin
                mem_write   = 1'b1;
                alu_src_imm = 1'b1;
                alu_op      = ALU_ADD;
            end
            OP_BRANCH: begin
                branch = 1'b1;
                alu_op = ALU_SUB; // comparisons done off a-b in the core
            end
            OP_JAL: begin
                reg_write = 1'b1;
                jump      = 1'b1;
            end
            OP_JALR: begin
                reg_write   = 1'b1;
                jump        = 1'b1;
                jalr        = 1'b1;
                alu_src_imm = 1'b1;
                alu_op      = ALU_ADD;
            end
            OP_LUI: begin
                reg_write = 1'b1;
                lui       = 1'b1;
            end
            OP_AUIPC: begin
                reg_write = 1'b1;
                auipc     = 1'b1;
            end
            OP_SYSTEM: begin
                // ECALL/EBREAK/FENCE: no architectural effect in this core (no traps).
            end
            default: illegal = 1'b1;
        endcase
    end
endmodule
