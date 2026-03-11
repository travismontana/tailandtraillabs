#include <furi.h>
#include <furi_hal_bt.h>
#include <gap.h>
#include <notification/notification_messages.h>

// Company IDs to flag
static const uint16_t watch_ids[] = {
    0x0043, // Ray-Ban Meta
    0x00DB, // Luxottica
    0x01AB,
    0x058E,
    0x0D53,
    0x03C2,
};

static void ble_ad_callback(GapLeScanResult* result, void* ctx) {
    NotificationApp* notif = ctx;
    uint8_t* data = result->data;
    uint8_t len = result->data_len;
    uint8_t i = 0;

    while(i < len) {
        uint8_t seg_len = data[i];
        uint8_t type    = data[i + 1];

        // 0xFF = Manufacturer Specific
        if(type == 0xFF && seg_len >= 3) {
            uint16_t company_id = data[i + 2] | (data[i + 3] << 8);

            for(size_t j = 0; j < COUNT_OF(watch_ids); j++) {
                if(company_id == watch_ids[j]) {
                    // Buzz
                    notification_message(notif, &sequence_double_vibro);
                    return;
                }
            }
        }
        i += seg_len + 1;
    }
}