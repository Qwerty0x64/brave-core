/* Copyright 2020 The Brave Authors. All rights reserved.
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this file,
 * You can obtain one at http://mozilla.org/MPL/2.0/. */

#include "brave/browser/brave_rewards/checkout_dialog_controller.h"

namespace brave_rewards {

CheckoutDialogController::CheckoutDialogController() = default;

CheckoutDialogController::~CheckoutDialogController() = default;

void CheckoutDialogController::NotifyAbort() {
  for (auto& observer : observers_) {
    observer.OnAbort();
  }
}

void CheckoutDialogController::NotifyComplete() {
  for (auto& observer : observers_) {
    observer.OnComplete();
  }
}

void CheckoutDialogController::SetOnDialogClosedCallback(
    OnDialogClosedCallback callback) {
  closed_callback_ = std::move(callback);
}

void CheckoutDialogController::AddObserver(Observer* observer) {
  observers_.AddObserver(observer);
}

void CheckoutDialogController::RemoveObserver(Observer* observer) {
  observers_.RemoveObserver(observer);
}

void CheckoutDialogController::NotifyDialogClosed() {
  if (closed_callback_) {
    std::move(closed_callback_).Run();
  }
}

}  // namespace brave_rewards
