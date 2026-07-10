module moore_nonol(
                   in                                       ,//input
                   clk                                      ,//clock
                   reset                                    ,//reset
                   out                                       //output
                   )                                        ;

//port declaration
input             in, clk, reset                            ;//input declaration
output reg        out                                       ;//output declaration
parameter         S0 = 0 , S1 = 1 , S2 = 2 , S3 = 3, S4 =4  ;//parameter declaration for states
reg       [2:0]   present_state,next_state                  ;//register declaration for states
reg               new_out                                   ;//ADDED: declare new_out

/*State S0 is assigned to present state if the reset is 1 else the next state is assigned to present state*/
always @ (posedge clk or posedge reset)
   begin
      if(reset)
         present_state <= S0                             ;//if reset is true then go to state S0
      else    
         present_state <= next_state                     ;//if reset is false then make next state as present state
   end             

/*Here the states S0, S1, S2, S3 or S4 is assigned according to the input encountered (for the sequence 1101)*/
always @ (present_state or in)
   begin      
     case(present_state)    
         S0 : begin
           	   if (in)
             		next_state    = S1                             ;//next state will be S1 if input is 1 otherwise S0
           		else
             		next_state    = S0                             ;
           		new_out  =  0                             ;//output is 0 till the desired sequence is acquired
              end
         S1 : begin 
              	if (in)
             		next_state    = S2                             ;//FIXED: was "ns" -> now "next_state"
           		else
             		next_state    = S0                             ;
           		new_out  =  0                             ;
              end
         S2 : begin 
              	if (in)
                  next_state    = S2                             ;//FIXED: was "ns"
           		else
             		next_state    = S3                             ;
           		new_out  =  0                             ;
              end 
       	 S3 : begin 
              	if (in)
                  next_state    = S4                             ;//FIXED: was "ns"
           		else
             		next_state    = S0                             ;
           		new_out  =  0                             ;
              end 
         S4 : begin 
              	if (in)
               	next_state    = S1                             ;//FIXED: was "ns"
           		else
             		next_state    = S0                             ;
           		new_out  =  1                             ;//output is 1 when the 1101 sequence is acquired
              end 
      endcase
   end

// FIX: assign output from new_out
always @ (new_out)
   out = new_out;

endmodule                                                //end of moore machine