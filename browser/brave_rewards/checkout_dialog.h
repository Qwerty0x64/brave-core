/* Copyright 2020 The Brave Authors. All rights reserved.
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this file,
 * You can obtain one at http://mozilla.org/MPL/2.0/. */

#ifndef BRAVE_BROWSER_BRAVE_REWARDS_CHECKOUT_DIALOG_H_
#define BRAVE_BROWSER_BRAVE_REWARDS_CHECKOUT_DIALOG_H_

#include <string>
#include "base/callback.h"

namespace content {
class WebContents;
}

namespace brave_rewards {

using CheckoutDialogClosedCallback = base::OnceCallback<void()>;

void ShowCheckoutDialog(
    content::WebContents* initiator,
    CheckoutDialogClosedCallback on_dialog_closed);

}

#endif  // BRAVE_BROWSER_BRAVE_REWARDS_CHECKOUT_DIALOG_H_
