import { Module } from '@nestjs/common';
import { SignalController } from './controllers/signal.controller';
import { SignalService } from './services/signal.service';

@Module({
  controllers: [SignalController],
  providers: [SignalService],
})
export class AppModule {} 