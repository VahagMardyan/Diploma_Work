module alu(
           a         ,  //input
           b         ,  //input
           select    ,  //input
           zero      ,  //zero flag
           carry     ,  //carry flag
           sign      ,  //sign flag
           parity    ,  //parity flag
           overflow  ,  //overflow flag
           out          //output
           )         ;
           
input [3:0]a, b                                 ;
input [1:0] select                              ;
output reg [3:0]out                             ;
output reg zero, carry, sign, parity, overflow  ;

always @ (*)
   begin
      // Default assignments to prevent latch inference
      carry = 1'b0;
      out   = 4'b0;
      
      case(select)
         2'b00 : {carry, out} = a + b   ;
         2'b01 : {carry, out} = a - b   ;
         2'b10 : {carry, out} = a * b   ;
         2'b11 : {carry, out} = a / b   ;
         default: {carry, out} = 1'bx;
      endcase

      zero     =  ~|out                                              ;
      sign     =  out[3]                                             ;
      parity   =  ~^out                                              ;
      overflow =  (a[3] & b[3] & ~out[3]) | (~a[3] & ~b[3] & out[3]) ;
   end
 
endmodule
