from rest_framework import permissions


class IsVerifiedHost(permissions.BasePermission):
    """
    Permission class to allow access only to verified hosts.
    Hosts must have verification_status='approved' to access protected endpoints.
    """

    message = "Your account is pending verification. Please upload your Aadhar card and wait for admin approval."

    def has_permission(self, request, view):
        # Check if user is authenticated
        if not request.user or not request.user.is_authenticated:
            return False

        # Check if user is a host
        if request.user.user_type != "host":
            self.message = "Only hosts can access this resource."
            return False

        # Check if host profile exists
        if not hasattr(request.user, "host_profile"):
            self.message = "Host profile not found."
            return False

        # Check verification status
        host_profile = request.user.host_profile
        if host_profile.verification_status != "approved":
            if host_profile.verification_status == "pending":
                if host_profile.aadhar_card_front and host_profile.aadhar_card_back:
                    self.message = (
                        "Your Aadhar card is under review. Please wait for admin approval to access this feature."
                    )
                else:
                    self.message = "Please upload your Aadhar card to complete verification."
            elif host_profile.verification_status == "rejected":
                rejection_reason = (
                    host_profile.verification_notes if host_profile.verification_notes else "No reason provided"
                )
                self.message = f"Your verification was rejected. Reason: {rejection_reason}. Please contact support."
            return False

        return True


class IsPlayerUser(permissions.BasePermission):
    """
    Permission class to allow access only to player users
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type == "player"
