module comparator_8bit (A, B, greater, equal, less);
        parameter n = 8;
        input [n - 1:0] A;
        input [n - 1:0] B;
        output reg greater;
        output reg equal;
        output reg less;

        always @ (*) begin
                greater = 0;
                equal = 0;
                less = 0;

                if (A > B)
                        greater = 1;
                else if (A == B)
                        equal = 1;
                else
                        less = 1;
        end
endmodule