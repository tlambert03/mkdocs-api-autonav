/**
 * @file arv.h
 * @brief Main ARV library header
 */

#ifndef ARV_H
#define ARV_H

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @brief Initialize the ARV library
 * @return 0 on success, -1 on error
 */
int arv_init(void);

/**
 * @brief Cleanup the ARV library
 */
void arv_cleanup(void);

/**
 * @brief Get library version
 * @return Version string
 */
const char* arv_get_version(void);

#ifdef __cplusplus
}
#endif

#endif /* ARV_H */