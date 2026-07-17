// mac_param.v - Multiply-Accumulate
module mac_param #(
    parameter DATA_W = 8,
    parameter ACC_W  = 16
)(
    input  wire                  clk,
    input  wire                  rst_n,
    input  wire                  en,
    input  wire signed [DATA_W-1:0] a,
    input  wire signed [DATA_W-1:0] b,
    input  wire                  acc_clear,
    output reg  signed [ACC_W-1:0] acc_out
);
    reg signed [ACC_W-1:0] prod;
    
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            prod    <= 0;
            acc_out <= 0;
        end else if (acc_clear) begin
            acc_out <= 0;
        end else if (en) begin
            prod    <= a * b;
            acc_out <= acc_out + prod;
        end
    end
endmodule
