from beaker.application import Application
from beaker.decorators import external, internal
from pyteal import (
    App,
    Assert,
    Btoi,
    Bytes,
    Concat,
    Extract,
    Global,
    If,
    InnerTxnBuilder,
    Int,
    Itob,
    Seq,
    Txn,
    TxnField,
    TxnType,
)
from pyteal.ast import abi


class MyApp(Application):
    contractFee = Int(1000000)

    @external
    def signup(
        self,
        affiliate: abi.Address,
        linkCreator: abi.Address,
        *,
        output: abi.Uint64,
    ):
        linkCreatorKey = Concat(
            linkCreator.get(),
            Bytes("c"),
        )
        return Seq(
            affilateBox := App.box_get(affiliate.get()),
            Assert(affilateBox.hasValue() == Int(0)),
            App.box_put(
                affiliate.get(),
                linkCreator.get(),
            ),
            linkCreatorBox := App.box_get(linkCreatorKey),
            App.box_put(
                linkCreatorKey,
                If(linkCreatorBox.hasValue() == Int(0))
                .Then(Itob(Int(1)))
                .Else(Itob(Btoi(linkCreatorBox.value()) + Int(1))),
            ),
            output.set(Int(1)),
        )

    @external
    def affiliate_transaction(
        self,
        payment: abi.PaymentTransaction,
        affiliate: abi.Address,
        platformIndex: abi.Uint64,
    ):
        affiliateKey = Concat(affiliate.get(), Itob(platformIndex.get()))
        creatorAlgoReceivedKey = Concat(affiliateKey, Bytes("a"))
        return Seq(
            affilateBox := App.box_get(affiliateKey),
            Assert(payment.get().sender() == Txn.sender()),
            Assert(payment.get().receiver() == Global.current_application_address()),
            Assert(affilateBox.hasValue() == Int(1)),
            self.handle_transactions(
                payment, Extract(affilateBox.value(), Int(0), Int(32))
            ),
            linkCreatorAmountBox := App.box_get(creatorAlgoReceivedKey),
            App.box_put(
                creatorAlgoReceivedKey,
                If(linkCreatorAmountBox.hasValue() == Int(0))
                .Then(Itob(Int(1)))
                .Else(
                    Itob(
                        Btoi(linkCreatorAmountBox.value())
                        + (payment.get().amount() - self.contractFee)
                    )
                ),
            ),
        )

    @internal
    def handle_transactions(
        self, payment: abi.PaymentTransaction, linkCreator: abi.Address
    ):
        return Seq(
            [
                InnerTxnBuilder.Begin(),
                InnerTxnBuilder.SetFields(
                    {
                        TxnField.type_enum: TxnType.Payment,
                        TxnField.sender: Global.current_application_address(),
                        TxnField.amount: Int(1000000),
                        TxnField.receiver: Global.creator_address(),
                    }
                ),
                InnerTxnBuilder.Next(),
                InnerTxnBuilder.SetFields(
                    {
                        TxnField.type_enum: TxnType.Payment,
                        TxnField.sender: Global.current_application_address(),
                        TxnField.amount: payment.get().amount() - self.contractFee,
                        TxnField.receiver: linkCreator,
                    }
                ),
                InnerTxnBuilder.Submit(),
            ]
        )
