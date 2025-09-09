/**
 * @file device.h
 * @brief Device management functions
 */

#ifndef ARV_DEVICE_H
#define ARV_DEVICE_H

#ifdef __cplusplus
extern "C" {
#endif

typedef struct ArvDevice ArvDevice;

/**
 * @brief Create a new device
 * @param name Device name
 * @return Device instance or NULL on error
 */
ArvDevice* arv_device_new(const char* name);

/**
 * @brief Free a device instance
 * @param device Device to free
 */
void arv_device_free(ArvDevice* device);

/**
 * @brief Get device name
 * @param device Device instance
 * @return Device name
 */
const char* arv_device_get_name(ArvDevice* device);

#ifdef __cplusplus
}
#endif

#endif /* ARV_DEVICE_H */