module seqmult(
    input  [7:0]  in_a,
    input  [7:0]  in_b,
    input         clk,
    input         load,
    input         reset,
    output reg    out_valid,
    output reg [15:0] out_prod
);

wire [15:0] temp_prod = {8'b0, in_b};
reg  [15:0] p1, p2, p3, p4, p5, p6, p7, p8;

always @ (posedge clk or posedge reset) begin
    if (reset) begin
        out_prod  <= 16'b0;
        out_valid <= 1'b0;
        p1 <= 16'b0; p2 <= 16'b0; p3 <= 16'b0; p4 <= 16'b0;
        p5 <= 16'b0; p6 <= 16'b0; p7 <= 16'b0; p8 <= 16'b0;
    end else begin
        if (load) begin
            p1 <= (in_a[0]) ? temp_prod      : 16'b0;
            p2 <= (in_a[1]) ? temp_prod << 1 : 16'b0;
            p3 <= (in_a[2]) ? temp_prod << 2 : 16'b0;
            p4 <= (in_a[3]) ? temp_prod << 3 : 16'b0;
            p5 <= (in_a[4]) ? temp_prod << 4 : 16'b0;
            p6 <= (in_a[5]) ? temp_prod << 5 : 16'b0;
            p7 <= (in_a[6]) ? temp_prod << 6 : 16'b0;
            p8 <= (in_a[7]) ? temp_prod << 7 : 16'b0;
            
            out_prod  <= p1 + p2 + p3 + p4 + p5 + p6 + p7 + p8;
            out_valid <= 1'b1;
        end else begin
            out_valid <= 1'b0;
        end
    end
end

endmodule
