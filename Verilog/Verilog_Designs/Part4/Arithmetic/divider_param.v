// divider_param.v - Parameterized restoring divider
module divider_param #(
    parameter WIDTH = 8
)(
    input  wire                clk,
    input  wire                rst_n,
    input  wire                start,
    input  wire [WIDTH-1:0]    dividend,
    input  wire [WIDTH-1:0]    divisor,
    output reg  [WIDTH-1:0]    quotient,
    output reg  [WIDTH-1:0]    remainder,
    output reg                 ready,
    output reg                 busy
);
    localparam CNT_W = $clog2(WIDTH+1);
    
    reg [WIDTH-1:0] r, b, q;
    reg [CNT_W-1:0] cnt;
    reg [1:0] state;
    
    localparam IDLE    = 2'b00,
               COMPUTE = 2'b01,
               DONE    = 2'b10;
    
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state     <= IDLE;
            busy      <= 1'b0;
            ready     <= 1'b0;
            quotient  <= 0;
            remainder <= 0;
            cnt       <= 0;
            r         <= 0;
            b         <= 0;
            q         <= 0;
        end else begin
            case (state)
                IDLE: begin
                    if (start) begin
                        r     <= 0;
                        b     <= divisor;
                        q     <= dividend;
                        cnt   <= WIDTH;
                        busy  <= 1'b1;
                        ready <= 1'b0;
                        state <= COMPUTE;
                    end
                end
                
                COMPUTE: begin
                    if (r >= b) begin
                        r <= r - b;
                        q <= {q[WIDTH-2:0], 1'b1};
                    end else begin
                        q <= {q[WIDTH-2:0], 1'b0};
                    end
                    r <= {r[WIDTH-2:0], q[WIDTH-1]};
                    cnt <= cnt - 1'b1;
                    if (cnt == 1) begin
                        state <= DONE;
                    end
                end
                
                DONE: begin
                    quotient  <= q;
                    remainder <= r;
                    ready     <= 1'b1;
                    busy      <= 1'b0;
                    state     <= IDLE;
                end
            endcase
        end
    end
endmodule
