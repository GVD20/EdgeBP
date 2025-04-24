#include <stdio.h>
#include <inttypes.h>
#include "sdkconfig.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_chip_info.h"
#include "esp_flash.h"
#include "esp_system.h"
#include "driver/gpio.h"
#include "myi2c.h"
#include "max30102.h"
#include "blood.h"
#include "esp_log.h"

max30102_handle_t max30102;
float temp, spo2, heart;
static const char *TAG = "main";
void max30102_task(void *p)
{
    while (1)
    {
        blood_Loop(max30102, &heart, &spo2);
    }
}

void app_main(void)
{
    ESP_ERROR_CHECK(i2c_master_init());

    max30102 = max30102_create(0, MAX30102_Device_address, GPIO_NUM_6);
    ESP_ERROR_CHECK(max30102_config(max30102));

    xTaskCreate(max30102_task, "max30102", 4096, NULL, 6, NULL);
}