module traffic_light_fsm (input clk, rst_n, output reg [2:0] lights);
    reg [1:0] state; reg [3:0] timer;
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin state <= 0; timer <= 0; lights <= 3'b100; end
        else begin
            timer <= timer + 1;
            case(state)
                0: if(timer == 10) begin state <= 1; timer <= 0; lights <= 3'b110; end 
                1: if(timer == 2)  begin state <= 2; timer <= 0; lights <= 3'b001; end 
                2: if(timer == 10) begin state <= 3; timer <= 0; lights <= 3'b010; end 
                3: if(timer == 2)  begin state <= 0; timer <= 0; lights <= 3'b100; end 
            endcase
        end
    end
endmodule