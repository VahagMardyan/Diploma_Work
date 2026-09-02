module johnson_counter (
    input clk,
    input rst_n,
    output reg [7:0] q
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            q <= 8'b00000000;
        else
            q <= {q[6:0], ~q[7]}; 
    end
endmodule