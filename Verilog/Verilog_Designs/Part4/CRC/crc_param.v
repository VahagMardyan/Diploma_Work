// crc_param.v - Sequential CRC (processes 8 bits per clock)
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
    reg [CRC_W-1:0] crc;
    integer i;
    
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            crc <= INIT;
        end else if (en) begin
            crc <= crc ^ { {CRC_W-8{1'b0}}, data_in };
            for (i=0; i<8; i=i+1) begin
                if (crc[CRC_W-1]) begin
                    crc <= {crc[CRC_W-2:0], 1'b0} ^ POLY;
                end else begin
                    crc <= {crc[CRC_W-2:0], 1'b0};
                end
            end
        end
    end
    
    assign crc_out = crc;
endmodule
