// i2c_master.v - I2C Master (single byte transfer)
module i2c_master (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       start,
    input  wire [6:0] slave_addr,
    input  wire       rw,         // 0=write, 1=read
    input  wire [7:0] tx_data,
    output reg  [7:0] rx_data,
    output reg        done,
    output wire       scl,
    inout  wire       sda
);
    localparam IDLE      = 4'h0,
               START_CND = 4'h1,
               ADDR      = 4'h2,
               ACK1      = 4'h3,
               DATA      = 4'h4,
               ACK2      = 4'h5,
               STOP_CND  = 4'h6;
    
    reg [3:0] state;
    reg [3:0] bit_cnt;
    reg [7:0] data_reg;
    reg       scl_reg;
    reg       sda_out;
    reg       sda_oe;
    reg       ack;
    
    assign scl = scl_reg;
    assign sda = sda_oe ? sda_out : 1'bz;
    
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state    <= IDLE;
            scl_reg  <= 1'b1;
            sda_out  <= 1'b1;
            sda_oe   <= 1'b1;
            done     <= 1'b0;
            bit_cnt  <= 0;
            data_reg <= 0;
            rx_data  <= 0;
        end else begin
            case (state)
                IDLE: begin
                    if (start) begin
                        sda_out <= 1'b0;        // Start condition
                        scl_reg <= 1'b1;
                        state   <= START_CND;
                        bit_cnt <= 0;
                        data_reg <= {slave_addr, rw};
                    end
                end
                START_CND: begin
                    scl_reg <= 1'b0;
                    state   <= ADDR;
                end
                ADDR: begin
                    if (bit_cnt < 8) begin
                        sda_out <= data_reg[7];
                        data_reg <= {data_reg[6:0], 1'b0};
                        bit_cnt  <= bit_cnt + 1;
                        scl_reg  <= 1'b1;
                    end else begin
                        scl_reg <= 1'b0;
                        sda_oe  <= 1'b0;        // Release for ACK
                        state   <= ACK1;
                        bit_cnt <= 0;
                    end
                end
                ACK1: begin
                    scl_reg <= 1'b1;
                    ack     <= sda;             // Read ACK
                    scl_reg <= 1'b0;
                    if (rw) begin
                        sda_oe <= 1'b0;         // Read mode
                    end else begin
                        sda_oe  <= 1'b1;
                        data_reg <= tx_data;
                    end
                    state <= DATA;
                end
                DATA: begin
                    if (bit_cnt < 8) begin
                        if (rw) begin
                            data_reg <= {data_reg[6:0], sda};
                        end else begin
                            sda_out <= data_reg[7];
                            data_reg <= {data_reg[6:0], 1'b0};
                        end
                        bit_cnt <= bit_cnt + 1;
                        scl_reg <= 1'b1;
                    end else begin
                        scl_reg <= 1'b0;
                        if (rw) begin
                            sda_oe  <= 1'b1;
                            sda_out <= 1'b1;    // NACK
                        end else begin
                            sda_oe <= 1'b0;     // Release for slave ACK
                        end
                        state <= ACK2;
                        bit_cnt <= 0;
                    end
                end
                ACK2: begin
                    scl_reg <= 1'b1;
                    if (rw) begin
                        rx_data <= data_reg;
                    end
                    scl_reg <= 1'b0;
                    state <= STOP_CND;
                end
                STOP_CND: begin
                    sda_oe  <= 1'b1;
                    sda_out <= 1'b0;
                    scl_reg <= 1'b1;
                    sda_out <= 1'b1;            // Stop condition
                    done    <= 1'b1;
                    state   <= IDLE;
                end
            endcase
        end
    end
endmodule
