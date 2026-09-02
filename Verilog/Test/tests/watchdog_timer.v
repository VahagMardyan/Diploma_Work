module watchdog_timer #(
    parameter W = 16
)(
    input clk,
    input rst_n,
    input feed,
    output reg timeout
);
    reg [W-1:0] count;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            count <= 0;
            timeout <= 0;
        end else if (feed) begin
            count <= 0;
            timeout <= 0;
        end else begin
            if (count == {W{1'b1}}) begin
                timeout <= 1;
            end else begin
                count <= count + 1;
            end
        end
    end
endmodule