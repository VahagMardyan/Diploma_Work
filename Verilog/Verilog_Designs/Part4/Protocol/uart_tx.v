// uart_tx.v - UART Transmitter (8-N-1)
module uart_tx (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       tx_en,
    input  wire [7:0] tx_data,
    output wire       tx_out,
    output wire       tx_busy
);
    localparam IDLE  = 2'b00,
               START = 2'b01,
               DATA  = 2'b10,
               STOP  = 2'b11;
    
    reg [1:0] state;
    reg [3:0] bit_cnt;
    reg [7:0] data_reg;
    reg       tx_reg;
    
    assign tx_out  = tx_reg;
    assign tx_busy = (state != IDLE);
    
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state    <= IDLE;
            tx_reg   <= 1'b1;
            bit_cnt  <= 0;
            data_reg <= 0;
        end else begin
            case (state)
                IDLE: begin
                    if (tx_en) begin
                        data_reg <= tx_data;
                        tx_reg   <= 1'b0;       // Start bit
                        state    <= START;
                    end
                end
                START: begin
                    tx_reg   <= data_reg[bit_cnt];
                    bit_cnt  <= bit_cnt + 1;
                    state    <= DATA;
                end
                DATA: begin
                    if (bit_cnt < 8) begin
                        tx_reg  <= data_reg[bit_cnt];
                        bit_cnt <= bit_cnt + 1;
                    end else begin
                        tx_reg <= 1'b1;         // Stop bit
                        state  <= STOP;
                    end
                end
                STOP: begin
                    state   <= IDLE;
                    bit_cnt <= 0;
                end
            endcase
        end
    end
endmodule
