module seq_detector_1011 (input clk, rst_n, din, output reg matched);
    reg [1:0] state, next_state;
    always @(posedge clk or negedge rst_n) if(!rst_n) state <= 0; else state <= next_state;
    always @(*) begin
        next_state = state; matched = 0;
        case(state)
            0: next_state = din ? 1 : 0;
            1: next_state = din ? 1 : 2;
            2: next_state = din ? 3 : 0;
            3: begin matched = din; next_state = din ? 1 : 2; end
        endcase
    end
endmodule