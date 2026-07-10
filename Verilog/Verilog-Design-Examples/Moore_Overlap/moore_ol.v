module moore_ol(
                in, clk, reset, out
                );

input       in, clk, reset;
output reg  out;
parameter   S0 = 3'b000 , S1 = 3'b001 , S2 = 3'b010 , S3 = 3'b011, S4 = 3'b100;
reg         [2:0] present_state, next_state;

always @ (posedge clk or posedge reset) begin
      if(reset) present_state <= S0;
      else      present_state <= next_state;
end             

always @ (*) begin      
   next_state = S0;
   out        = 0;

   case(present_state)  
      S0 : if (in) next_state = S1; else next_state = S0;
      S1 : if (in) next_state = S2; else next_state = S0;
      S2 : if (in) next_state = S2; else next_state = S3;
      S3 : if (in) next_state = S4; else next_state = S0;
      S4 : begin 
              out = 1;
              if (in) next_state = S2; else next_state = S0;
           end
      default: begin next_state = S0; out = 0; end
   endcase
end
endmodule
