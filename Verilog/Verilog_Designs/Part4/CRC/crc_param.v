module crc_param #(
    parameter CRC_W = 8,
    parameter [CRC_W-1:0] POLY = 8'h07,   // CRC-8-CCITT: 0x07
    parameter [CRC_W-1:0] INIT = 8'hFF
)(
    input  wire               clk,
    input  wire               rst_n,
    input  wire               en,
    input  wire [7:0]         data_in,
    output reg  [CRC_W-1:0]   crc_out
);

    reg [CRC_W-1:0] crc_comb;
    integer i;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            crc_out <= INIT;
        end else if (en) begin
            crc_out <= crc_comb;
        end
    end

    always @(*) begin
        crc_comb = crc_out;
        
        crc_comb[7:0] = crc_comb[7:0] ^ data_in;
        
        for (i = 0; i < 8; i = i + 1) begin
            if (crc_comb[CRC_W-1]) begin
                crc_comb = {crc_comb[CRC_W-2:0], 1'b0} ^ POLY;
            end else begin
                crc_comb = {crc_comb[CRC_W-2:0], 1'b0};
            end
        end
    end

endmodule