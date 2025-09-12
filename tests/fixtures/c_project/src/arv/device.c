/**
 * @file device.c
 * @brief Device management implementation
 */

#include "device.h"
#include <stdlib.h>
#include <string.h>

struct ArvDevice {
    char* name;
};

/**
 * @brief Create a new device
 * @param name Device name
 * @return Device instance or NULL on error
 */
ArvDevice* arv_device_new(const char* name) {
    if (!name) {
        return NULL;
    }
    
    ArvDevice* device = malloc(sizeof(ArvDevice));
    if (!device) {
        return NULL;
    }
    
    device->name = strdup(name);
    if (!device->name) {
        free(device);
        return NULL;
    }
    
    return device;
}

/**
 * @brief Free a device instance
 * @param device Device to free
 */
void arv_device_free(ArvDevice* device) {
    if (!device) {
        return;
    }
    
    free(device->name);
    free(device);
}

/**
 * @brief Get device name
 * @param device Device instance
 * @return Device name
 */
const char* arv_device_get_name(ArvDevice* device) {
    if (!device) {
        return NULL;
    }
    
    return device->name;
}