#define _GNU_SOURCE

#include <arpa/inet.h>
#include <errno.h>
#include <netinet/in.h>
#include <stddef.h>
#include <stdint.h>
#include <sys/socket.h>
#include <sys/syscall.h>
#include <unistd.h>


static int ipv4_is_loopback(const struct in_addr *address) {
    const uint32_t host = ntohl(address->s_addr);
    return (host & 0xff000000U) == 0x7f000000U;
}


static int address_is_local(
    const struct sockaddr *address,
    socklen_t address_length
) {
    if (address == NULL) {
        return 1;
    }
    if (address->sa_family == AF_INET) {
        if (address_length < sizeof(struct sockaddr_in)) {
            return 0;
        }
        const struct sockaddr_in *ipv4 =
            (const struct sockaddr_in *)address;
        return ipv4_is_loopback(&ipv4->sin_addr);
    }
    if (address->sa_family == AF_INET6) {
        if (address_length < sizeof(struct sockaddr_in6)) {
            return 0;
        }
        const struct sockaddr_in6 *ipv6 =
            (const struct sockaddr_in6 *)address;
        if (IN6_IS_ADDR_LOOPBACK(&ipv6->sin6_addr)) {
            return 1;
        }
        if (IN6_IS_ADDR_V4MAPPED(&ipv6->sin6_addr)) {
            struct in_addr mapped;
            const unsigned char *bytes = ipv6->sin6_addr.s6_addr;
            mapped.s_addr =
                ((uint32_t)bytes[12]) |
                ((uint32_t)bytes[13] << 8U) |
                ((uint32_t)bytes[14] << 16U) |
                ((uint32_t)bytes[15] << 24U);
            return ipv4_is_loopback(&mapped);
        }
        return 0;
    }
    return 1;
}


int connect(
    int socket_descriptor,
    const struct sockaddr *address,
    socklen_t address_length
) {
    if (!address_is_local(address, address_length)) {
        errno = EACCES;
        return -1;
    }
    return (int)syscall(
        SYS_connect,
        socket_descriptor,
        address,
        address_length
    );
}


int bind(
    int socket_descriptor,
    const struct sockaddr *address,
    socklen_t address_length
) {
    if (!address_is_local(address, address_length)) {
        errno = EACCES;
        return -1;
    }
    return (int)syscall(
        SYS_bind,
        socket_descriptor,
        address,
        address_length
    );
}


ssize_t sendto(
    int socket_descriptor,
    const void *buffer,
    size_t length,
    int flags,
    const struct sockaddr *destination,
    socklen_t destination_length
) {
    if (!address_is_local(destination, destination_length)) {
        errno = EACCES;
        return -1;
    }
    return (ssize_t)syscall(
        SYS_sendto,
        socket_descriptor,
        buffer,
        length,
        flags,
        destination,
        destination_length
    );
}


ssize_t sendmsg(
    int socket_descriptor,
    const struct msghdr *message,
    int flags
) {
    if (
        message != NULL &&
        !address_is_local(
            (const struct sockaddr *)message->msg_name,
            message->msg_namelen
        )
    ) {
        errno = EACCES;
        return -1;
    }
    return (ssize_t)syscall(
        SYS_sendmsg,
        socket_descriptor,
        message,
        flags
    );
}
