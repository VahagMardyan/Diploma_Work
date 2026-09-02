module pwm_generator #(
    parameter RES = 8 // Resolution
)(
    input clk,
    input rst_n,
    input [RES-1:0] duty_cycle,
    output reg pwm_out
);
    reg [RES-1:0] counter;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            counter <= 0;
            pwm_out <= 0;
        end else begin
            counter <= counter + 1;
            if (counter < duty_cycle)
                pwm_out <= 1;
            else
                pwm_out <= 0;
        end
    end
endmodule